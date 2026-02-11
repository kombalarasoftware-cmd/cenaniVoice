"""
Audio Bridge - Connects Asterisk audio stream with OpenAI Realtime API
Handles bidirectional audio streaming and transcoding
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup

from app.services.openai_realtime import OpenAIRealtimeClient, RealtimeConfig, build_system_prompt, build_tools
from app.services.asterisk_ari import AsteriskARIClient, ARIConfig

logger = logging.getLogger(__name__)


@dataclass
class CallSession:
    """Represents an active call session"""
    call_id: str
    channel_id: str
    customer_phone: str
    customer_name: Optional[str]
    agent_config: Dict[str, Any]
    customer_data: Dict[str, Any]
    
    # State
    started_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Results
    transcription: Optional[list] = None
    outcome: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None  # positive, neutral, negative
    payment_promise: Optional[Dict] = None
    callback_scheduled: Optional[str] = None
    
    def __post_init__(self):
        self.started_at = datetime.utcnow()
        self.transcription = []


class AudioBridge:
    """
    Bridges audio between Asterisk and OpenAI Realtime API
    
    Flow:
    1. Asterisk receives inbound audio from customer
    2. AudioBridge forwards audio to OpenAI Realtime API
    3. OpenAI generates response audio
    4. AudioBridge forwards response to Asterisk
    5. Asterisk sends audio to customer
    """
    
    def __init__(
        self,
        openai_api_key: str,
        asterisk_config: Optional[ARIConfig] = None,
        on_call_complete: Optional[Callable[[CallSession], None]] = None
    ):
        self.openai_api_key = openai_api_key
        self.asterisk_config = asterisk_config or ARIConfig()
        self.on_call_complete = on_call_complete
        
        # Active sessions
        self.sessions: Dict[str, CallSession] = {}
        self.openai_clients: Dict[str, OpenAIRealtimeClient] = {}
        
        # Asterisk client (shared)
        self.asterisk: Optional[AsteriskARIClient] = None
    
    async def start(self):
        """Start the audio bridge"""
        # Connect to Asterisk
        self.asterisk = AsteriskARIClient(
            config=self.asterisk_config,
            on_call_start=self._handle_call_start,
            on_call_answer=self._handle_call_answer,
            on_call_end=self._handle_call_end,
            on_audio=self._handle_asterisk_audio
        )
        await self.asterisk.connect()
        
        logger.info("AudioBridge started")
    
    async def originate_call(
        self,
        call_id: str,
        phone_number: str,
        customer_name: str,
        agent_config: Dict[str, Any],
        customer_data: Dict[str, Any],
        trunk_name: str = "trunk"
    ) -> str:
        """
        Originate an outbound call
        
        Args:
            call_id: Unique call identifier
            phone_number: Phone number to call
            customer_name: Customer name for personalization
            agent_config: Agent configuration from database
            customer_data: Custom customer data for prompt variables
            trunk_name: SIP trunk name
        
        Returns:
            Channel ID
        """
        # Create session
        session = CallSession(
            call_id=call_id,
            channel_id="",  # Will be set after originate
            customer_phone=phone_number,
            customer_name=customer_name,
            agent_config=agent_config,
            customer_data=customer_data
        )
        
        # Format endpoint
        endpoint = f"PJSIP/{phone_number}@{trunk_name}"
        
        # Originate call via Asterisk
        if not self.asterisk:
            raise Exception("Asterisk client not initialized")
        
        channel_id = await self.asterisk.originate_call(
            endpoint=endpoint,
            caller_id=agent_config.get("caller_id", phone_number),
            variables={
                "CALL_ID": call_id,
                "CUSTOMER_NAME": customer_name or ""
            }
        )
        
        session.channel_id = channel_id
        self.sessions[channel_id] = session
        
        logger.info(f"Originated call {call_id} to {phone_number}")
        return channel_id
    
    async def _handle_call_start(self, channel_id: str, channel_data: dict):
        """Handle new call in Stasis"""
        logger.info(f"Call started: {channel_id}")
        
        # Answer the call
        if self.asterisk:
            await self.asterisk.answer_channel(channel_id)
    
    async def _handle_call_answer(self, channel_id: str, channel_data: dict):
        """Handle call answered"""
        logger.info(f"Call answered: {channel_id}")
        
        session = self.sessions.get(channel_id)
        if not session:
            logger.warning(f"No session found for channel {channel_id}")
            return
        
        session.connected_at = datetime.utcnow()
        
        # Start recording if enabled
        if session.agent_config.get("record_calls", True) and self.asterisk:
            await self.asterisk.start_recording(
                channel_id,
                name=f"call_{session.call_id}",
                format="wav"
            )
        
        # Connect to OpenAI Realtime API
        await self._connect_openai(channel_id, session)
    
    async def _connect_openai(self, channel_id: str, session: CallSession):
        """Connect OpenAI Realtime API for the call"""
        # Build configuration with all VAD and interrupt settings
        config = RealtimeConfig(
            voice=session.agent_config.get("voice", "alloy"),
            language=session.agent_config.get("language", "tr"),
            temperature=session.agent_config.get("temperature", 0.7),
            # VAD settings - optimized for interruption handling
            turn_detection_type=session.agent_config.get("turn_detection", "server_vad"),
            turn_detection_threshold=session.agent_config.get("vad_threshold", 0.3),
            turn_detection_prefix_padding_ms=session.agent_config.get("prefix_padding_ms", 500),
            turn_detection_silence_duration_ms=session.agent_config.get("silence_duration_ms", 800),
            # Interrupt handling - critical for natural conversation
            interrupt_response=session.agent_config.get("interrupt_response", True),
            create_response=session.agent_config.get("create_response", True),
            noise_reduction=session.agent_config.get("noise_reduction", True),
        )
        
        # Build system prompt with customer data
        system_prompt = build_system_prompt(
            session.agent_config,
            {
                "name": session.customer_name,
                "phone": session.customer_phone,
                **session.customer_data
            }
        )
        
        # Build tools
        tools = build_tools(session.agent_config)
        
        # Create OpenAI client
        client = OpenAIRealtimeClient(
            api_key=self.openai_api_key,
            config=config,
            on_audio=lambda audio: self._handle_openai_audio(channel_id, audio),
            on_transcript=lambda role, text: self._handle_transcript(channel_id, role, text),
            on_tool_call=lambda name, args: self._handle_tool_call(channel_id, name, args),
            on_error=lambda error: self._handle_openai_error(channel_id, error)
        )
        
        await client.connect(system_prompt, tools)
        self.openai_clients[channel_id] = client
        
        logger.info(f"OpenAI connected for channel {channel_id}")
    
    async def _handle_call_end(self, channel_id: str, channel_data: dict):
        """Handle call ended"""
        logger.info(f"Call ended: {channel_id}")
        
        session = self.sessions.get(channel_id)
        if session:
            session.ended_at = datetime.utcnow()
            
            # Stop recording
            if session.agent_config.get("record_calls", True) and self.asterisk:
                try:
                    await self.asterisk.stop_recording(f"call_{session.call_id}")
                except:
                    pass
            
            # Disconnect OpenAI
            client = self.openai_clients.get(channel_id)
            if client:
                await client.disconnect()
                del self.openai_clients[channel_id]
            
            # Callback with results
            if self.on_call_complete:
                self.on_call_complete(session)
            
            # Cleanup
            del self.sessions[channel_id]
    
    async def _handle_asterisk_audio(self, channel_id: str, audio_bytes: bytes):
        """Handle audio from Asterisk (customer speaking)"""
        client = self.openai_clients.get(channel_id)
        if client and client.is_connected:
            await client.send_audio(audio_bytes)
    
    def _handle_openai_audio(self, channel_id: str, audio_bytes: bytes):
        """Handle audio from OpenAI (AI speaking)"""
        # Send to Asterisk
        # Note: This would need to be done via external media in production
        if self.asterisk:
            asyncio.create_task(self.asterisk.send_audio(channel_id, audio_bytes))
    
    def _handle_transcript(self, channel_id: str, role: str, text: str):
        """Handle transcription from OpenAI"""
        session = self.sessions.get(channel_id)
        if session and session.transcription is not None:
            session.transcription.append({
                "role": role,
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            })
            logger.debug(f"[{channel_id}] {role}: {text}")
    
    async def _handle_tool_call(self, channel_id: str, name: str, args: dict) -> Any:
        """Handle tool call from OpenAI"""
        session = self.sessions.get(channel_id)
        if not session:
            return {"error": "Session not found"}
        
        logger.info(f"Tool call [{channel_id}]: {name}({args})")
        
        if name == "record_payment_promise":
            session.payment_promise = {
                "amount": args.get("amount"),
                "date": args.get("date"),
                "notes": args.get("notes")
            }
            return {"success": True, "message": "Payment promise recorded"}
        
        elif name == "save_customer_data":
            data_type = args.get("data_type", "")
            value = args.get("value", "")
            confirmed = args.get("confirmed", False)

            if not confirmed:
                return {"success": False, "message": "Customer has not confirmed yet. Please verify the data."}

            try:
                from app.core.database import SessionLocal
                from app.models.models import CallLog

                call_id = session.agent_config.get("call_id")
                with SessionLocal() as db:
                    call_log = db.query(CallLog).filter(CallLog.call_sid == call_id).first()
                    if call_log and data_type == "name":
                        call_log.customer_name = value
                        db.commit()
            except Exception as e:
                logger.error(f"save_customer_data DB error: {e}")

            logger.info(f"[{channel_id}] Customer {data_type} saved: {value}")
            return {"success": True, "message": f"{data_type} saved: {value}"}

        elif name == "set_call_sentiment":
            sentiment = args.get("sentiment", "neutral")
            reason = args.get("reason", "")
            session.sentiment = sentiment

            try:
                from app.core.database import SessionLocal
                from app.models.models import CallLog

                call_id = session.agent_config.get("call_id")
                with SessionLocal() as db:
                    call_log = db.query(CallLog).filter(CallLog.call_sid == call_id).first()
                    if call_log:
                        call_log.sentiment = sentiment
                        db.commit()
            except Exception as e:
                logger.error(f"set_call_sentiment DB error: {e}")

            logger.info(f"[{channel_id}] Sentiment: {sentiment} - {reason}")
            return {"success": True, "message": f"Sentiment recorded: {sentiment}"}

        elif name == "add_call_tags":
            tags = args.get("tags", [])

            try:
                from app.core.database import SessionLocal
                from app.models.models import CallLog

                call_id = session.agent_config.get("call_id")
                with SessionLocal() as db:
                    call_log = db.query(CallLog).filter(CallLog.call_sid == call_id).first()
                    if call_log:
                        existing = call_log.tags or []
                        call_log.tags = list(set(existing + tags))
                        db.commit()
            except Exception as e:
                logger.error(f"add_call_tags DB error: {e}")

            logger.info(f"[{channel_id}] Tags added: {tags}")
            return {"success": True, "message": f"Tags added: {', '.join(tags)}"}

        elif name == "generate_call_summary":
            summary_text = args.get("summary", "")
            action_items = args.get("action_items", [])
            satisfaction = args.get("customer_satisfaction", "neutral")
            session.summary = summary_text

            try:
                from app.core.database import SessionLocal
                from app.models.models import CallLog

                call_id = session.agent_config.get("call_id")
                with SessionLocal() as db:
                    call_log = db.query(CallLog).filter(CallLog.call_sid == call_id).first()
                    if call_log:
                        call_log.summary = summary_text
                        db.commit()
            except Exception as e:
                logger.error(f"generate_call_summary DB error: {e}")

            logger.info(f"[{channel_id}] Summary: {summary_text[:100]}...")
            return {"success": True, "message": "Call summary saved"}

        elif name == "transfer_to_human":
            reason = args.get("reason", "Customer request")
            
            # Transfer the call
            # await self.asterisk.transfer_call(channel_id, "PJSIP/operator")
            
            session.outcome = "transferred"
            return {"success": True, "message": f"Transferring: {reason}"}
        
        elif name == "schedule_callback":
            session.callback_scheduled = args.get("datetime")
            return {"success": True, "message": "Callback scheduled"}
        
        elif name == "end_call":
            session.outcome = args.get("outcome", "completed")
            session.summary = args.get("summary", "")
            session.sentiment = args.get("sentiment", "neutral")
            
            logger.info(f"Call ending [{channel_id}]: outcome={session.outcome}, sentiment={session.sentiment}")
            
            # End the call after a short delay (allows AI to say goodbye)
            asyncio.create_task(self._delayed_hangup(channel_id, 2))
            
            return {"success": True, "message": "Ending call"}
        
        elif name == "search_web_source":
            query = args.get("query", "")
            source_name = args.get("source_name", "")
            
            # Get web sources from agent config
            web_sources = session.agent_config.get("web_sources", [])
            if not web_sources:
                return {
                    "success": False,
                    "message": "No web sources configured for this agent. Answer with what you know.",
                    "results": []
                }
            
            # Search in specified source or all sources
            results = []
            for source in web_sources:
                if source_name and source.get("name", "") != source_name:
                    continue
                    
                url = source.get("url", "")
                if not url:
                    continue
                    
                try:
                    content = await self._fetch_web_content(url, query)
                    if content:
                        results.append({
                            "source": source.get("name", url),
                            "content": content[:2000]  # Limit content length
                        })
                except Exception as e:
                    logger.error(f"Web fetch error for {url}: {e}")
            
            if results:
                return {
                    "success": True,
                    "results": results,
                    "message": f"Found information from {len(results)} source(s)"
                }
            else:
                return {
                    "success": False,
                    "results": [],
                    "message": "No information found on this topic"
                }
        
        elif name == "search_documents":
            query = args.get("query", "")
            
            if not query:
                return {
                    "success": False,
                    "message": "Search query cannot be empty",
                    "results": []
                }
            
            # Perform semantic search using document service
            try:
                from app.services.document_service import DocumentService
                from app.core.database import AsyncSessionLocal
                
                async with AsyncSessionLocal() as db:
                    service = DocumentService(db)
                    agent_id = session.agent_config.get("agent_id")
                    
                    if not agent_id:
                        return {
                            "success": False,
                            "message": "Agent ID not found",
                            "results": []
                        }
                    
                    results = await service.semantic_search(
                        agent_id=agent_id,
                        query=query,
                        limit=5
                    )
                    
                    if results:
                        # Format results for AI
                        formatted_results = []
                        for r in results:
                            formatted_results.append({
                                "content": r["content"],
                                "source": r["document_filename"],
                                "relevance": f"{r['score']:.2f}"
                            })
                        
                        return {
                            "success": True,
                            "results": formatted_results,
                            "message": f"Found information from {len(results)} document(s)"
                        }
                    else:
                        return {
                            "success": False,
                            "results": [],
                            "message": "No matching information found in uploaded documents"
                        }
                        
            except Exception as e:
                logger.error(f"Document search error: {e}")
                return {
                    "success": False,
                    "message": "Document search failed",
                    "results": []
                }
        
        elif name == "confirm_appointment":
            # Extract appointment data from args
            customer_name = args.get("customer_name", "")
            customer_phone = args.get("customer_phone", "")
            customer_address = args.get("customer_address", "")
            appointment_date = args.get("appointment_date", "")
            appointment_time = args.get("appointment_time", "")
            appointment_type = args.get("appointment_type", "consultation")
            notes = args.get("notes", "")
            
            if not customer_name or not appointment_date or not appointment_time:
                return {
                    "success": False,
                    "message": "Customer name, date, and time are required for appointment"
                }
            
            try:
                from datetime import datetime as dt
                from app.models.models import Appointment, AppointmentType, AppointmentStatus
                from app.core.database import SessionLocal
                
                # Parse date
                try:
                    parsed_date = dt.strptime(appointment_date, "%Y-%m-%d")
                except ValueError:
                    return {
                        "success": False,
                        "message": f"Invalid date format: {appointment_date}. Must be YYYY-MM-DD."
                    }
                
                # Map appointment type
                type_map = {
                    "consultation": AppointmentType.CONSULTATION,
                    "site_visit": AppointmentType.SITE_VISIT,
                    "installation": AppointmentType.INSTALLATION,
                    "maintenance": AppointmentType.MAINTENANCE,
                    "demo": AppointmentType.DEMO,
                    "other": AppointmentType.OTHER,
                }
                apt_type = type_map.get(appointment_type, AppointmentType.CONSULTATION)
                
                # Get agent and call info from session
                agent_id = session.agent_config.get("agent_id")
                call_id = session.agent_config.get("call_id")
                campaign_id = session.agent_config.get("campaign_id")
                
                # Create appointment record
                with SessionLocal() as db:
                    appointment = Appointment(
                        agent_id=agent_id,
                        call_id=call_id,
                        campaign_id=campaign_id,
                        customer_name=customer_name,
                        customer_phone=customer_phone or session.agent_config.get("customer_phone"),
                        customer_address=customer_address,
                        appointment_type=apt_type,
                        appointment_date=parsed_date,
                        appointment_time=appointment_time,
                        status=AppointmentStatus.CONFIRMED,
                        notes=notes,
                        confirmed_at=dt.utcnow()
                    )
                    db.add(appointment)
                    db.commit()
                    
                    logger.info(f"Appointment created: {customer_name} - {appointment_date} {appointment_time}")
                    
                    return {
                        "success": True,
                        "appointment_id": appointment.id,
                        "message": f"Appointment created: {customer_name}, {appointment_date} at {appointment_time}",
                        "details": {
                            "customer_name": customer_name,
                            "date": appointment_date,
                            "time": appointment_time,
                            "type": appointment_type
                        }
                    }
                    
            except Exception as e:
                logger.error(f"Appointment creation error: {e}")
                return {
                    "success": False,
                    "message": "Failed to create appointment"
                }
        
        elif name == "capture_lead":
            # Extract lead data from args
            customer_name = args.get("customer_name", "")
            customer_phone = args.get("customer_phone", "")
            customer_email = args.get("customer_email", "")
            customer_address = args.get("customer_address", "")
            interest_type = args.get("interest_type", "information")
            customer_statement = args.get("customer_statement", "")
            priority = args.get("priority", 2)
            notes = args.get("notes", "")
            
            if not customer_name or not interest_type:
                return {
                    "success": False,
                    "message": "Customer name and interest type are required for lead"
                }
            
            try:
                from datetime import datetime as dt
                from app.models.models import Lead, LeadStatus, LeadInterestType
                from app.core.database import SessionLocal
                
                # Map interest type
                interest_map = {
                    "callback": LeadInterestType.CALLBACK,
                    "address_collection": LeadInterestType.ADDRESS_COLLECTION,
                    "purchase_intent": LeadInterestType.PURCHASE_INTENT,
                    "demo_request": LeadInterestType.DEMO_REQUEST,
                    "quote_request": LeadInterestType.QUOTE_REQUEST,
                    "subscription": LeadInterestType.SUBSCRIPTION,
                    "information": LeadInterestType.INFORMATION,
                    "other": LeadInterestType.OTHER,
                }
                lead_interest = interest_map.get(interest_type, LeadInterestType.INFORMATION)
                
                # Get agent and call info from session
                agent_id = session.agent_config.get("agent_id")
                call_id = session.agent_config.get("call_id")
                campaign_id = session.agent_config.get("campaign_id")
                
                # Create lead record
                with SessionLocal() as db:
                    lead = Lead(
                        agent_id=agent_id,
                        call_id=call_id,
                        campaign_id=campaign_id,
                        customer_name=customer_name,
                        customer_phone=customer_phone or session.agent_config.get("customer_phone"),
                        customer_email=customer_email,
                        customer_address=customer_address,
                        interest_type=lead_interest,
                        customer_statement=customer_statement,
                        status=LeadStatus.NEW,
                        priority=priority,
                        notes=notes
                    )
                    db.add(lead)
                    db.commit()
                    
                    # Translate interest type for response
                    interest_names = {
                        "callback": "callback request",
                        "address_collection": "address collection",
                        "purchase_intent": "purchase intent",
                        "demo_request": "demo request",
                        "quote_request": "quote request",
                        "subscription": "subscription",
                        "information": "information request",
                        "other": "other interest"
                    }
                    interest_name = interest_names.get(interest_type, interest_type)

                    logger.info(f"Lead captured: {customer_name} - {interest_type} (priority: {priority})")

                    return {
                        "success": True,
                        "lead_id": lead.id,
                        "message": f"Lead captured: {customer_name} - {interest_name}",
                        "details": {
                            "customer_name": customer_name,
                            "interest_type": interest_type,
                            "priority": priority,
                            "statement": customer_statement
                        }
                    }
                    
            except Exception as e:
                logger.error(f"Lead capture error: {e}")
                return {
                    "success": False,
                    "message": "Failed to capture lead"
                }
        
        elif name == "get_caller_datetime":
            # Get caller's local datetime based on phone number timezone
            try:
                import phonenumbers
                from datetime import datetime as dt
                import pytz
                
                customer_phone = session.agent_config.get("customer_phone", "")
                
                # Default timezone
                timezone_str = "Europe/Istanbul"  # Default to Turkey
                country_code = "TR"
                
                if customer_phone:
                    try:
                        # Parse phone number to get country code
                        parsed = phonenumbers.parse(customer_phone, None)
                        country_code = phonenumbers.region_code_for_number(parsed)
                        
                        # Country to timezone mapping (common ones)
                        country_timezones = {
                            "TR": "Europe/Istanbul",
                            "DE": "Europe/Berlin",
                            "FR": "Europe/Paris",
                            "GB": "Europe/London",
                            "US": "America/New_York",
                            "RU": "Europe/Moscow",
                            "SA": "Asia/Riyadh",
                            "AE": "Asia/Dubai",
                            "JP": "Asia/Tokyo",
                            "CN": "Asia/Shanghai",
                            "IN": "Asia/Kolkata",
                            "AU": "Australia/Sydney",
                            "BR": "America/Sao_Paulo",
                            "NL": "Europe/Amsterdam",
                            "BE": "Europe/Brussels",
                            "AT": "Europe/Vienna",
                            "CH": "Europe/Zurich",
                            "IT": "Europe/Rome",
                            "ES": "Europe/Madrid",
                            "PT": "Europe/Lisbon",
                            "PL": "Europe/Warsaw",
                            "GR": "Europe/Athens",
                            "CZ": "Europe/Prague",
                            "SE": "Europe/Stockholm",
                            "NO": "Europe/Oslo",
                            "DK": "Europe/Copenhagen",
                            "FI": "Europe/Helsinki",
                            "IE": "Europe/Dublin",
                            "IL": "Asia/Jerusalem",
                            "EG": "Africa/Cairo",
                            "ZA": "Africa/Johannesburg",
                            "KR": "Asia/Seoul",
                            "SG": "Asia/Singapore",
                            "MY": "Asia/Kuala_Lumpur",
                            "TH": "Asia/Bangkok",
                            "ID": "Asia/Jakarta",
                            "PH": "Asia/Manila",
                            "VN": "Asia/Ho_Chi_Minh",
                            "MX": "America/Mexico_City",
                            "AR": "America/Argentina/Buenos_Aires",
                            "CL": "America/Santiago",
                            "CO": "America/Bogota",
                            "PE": "America/Lima",
                            "CA": "America/Toronto",
                            "NZ": "Pacific/Auckland",
                            "PK": "Asia/Karachi",
                            "BD": "Asia/Dhaka",
                            "UA": "Europe/Kiev",
                            "RO": "Europe/Bucharest",
                            "HU": "Europe/Budapest",
                            "BG": "Europe/Sofia",
                            "HR": "Europe/Zagreb",
                            "RS": "Europe/Belgrade",
                            "AZ": "Asia/Baku",
                            "GE": "Asia/Tbilisi",
                            "KZ": "Asia/Almaty",
                            "UZ": "Asia/Tashkent",
                        }
                        
                        if country_code in country_timezones:
                            timezone_str = country_timezones[country_code]
                        else:
                            # Try to get timezone from pytz for this country
                            country_tzs = pytz.country_timezones.get(country_code, [])
                            if country_tzs:
                                timezone_str = country_tzs[0]
                                
                    except Exception as parse_error:
                        logger.warning(f"Phone number parse error: {parse_error}")
                
                # Get current time in the timezone
                tz = pytz.timezone(timezone_str)
                now = dt.now(tz)
                
                # Determine greeting based on hour
                hour = now.hour
                if 5 <= hour < 12:
                    greeting = "Günaydın"
                    time_of_day = "sabah"
                elif 12 <= hour < 18:
                    greeting = "İyi günler"
                    time_of_day = "öğleden sonra"
                elif 18 <= hour < 22:
                    greeting = "İyi akşamlar"
                    time_of_day = "akşam"
                else:
                    greeting = "İyi geceler"
                    time_of_day = "gece"
                
                # Format date in Turkish
                days_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
                months_tr = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
                
                day_name = days_tr[now.weekday()]
                month_name = months_tr[now.month - 1]
                
                return {
                    "success": True,
                    "datetime": {
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M"),
                        "day_of_week": day_name,
                        "day": now.day,
                        "month": month_name,
                        "year": now.year,
                        "hour": now.hour,
                        "minute": now.minute,
                        "timezone": timezone_str,
                        "country_code": country_code,
                    },
                    "greeting": greeting,
                    "time_of_day": time_of_day,
                    "formatted_date": f"{now.day} {month_name} {now.year}, {day_name}",
                    "formatted_time": now.strftime("%H:%M"),
                    "message": f"Customer local time: {now.strftime('%H:%M')} ({timezone_str}). Suggested greeting: {greeting}"
                }
                
            except Exception as e:
                logger.error(f"Get caller datetime error: {e}")
                # Return default Turkey time on error
                from datetime import datetime as dt
                import pytz
                tz = pytz.timezone("Europe/Istanbul")
                now = dt.now(tz)
                return {
                    "success": True,
                    "datetime": {
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M"),
                        "timezone": "Europe/Istanbul",
                    },
                    "greeting": "Hello",
                    "message": f"Default time used: {now.strftime('%H:%M')} (Turkey)"
                }
        
        elif name == "verify_contact_info":
            # ================================================================
            # CONTACT INFO VERIFICATION HANDLER
            # Multi-language (TR/DE/EN) phone, email, address, name validation
            # ================================================================
            import re
            
            info_type = args.get("info_type", "")
            raw_value = args.get("raw_value", "").strip()
            language = args.get("language", "auto")
            
            if not info_type or not raw_value:
                return {
                    "success": False,
                    "error": "missing_params",
                    "message": {
                        "tr": "Bilgi tipi ve değer gereklidir.",
                        "de": "Infotyp und Wert sind erforderlich.",
                        "en": "Info type and value are required."
                    }.get(language, "Info type and value are required.")
                }
            
            # ---- Auto-detect language if needed ----
            if language == "auto":
                # Simple heuristic based on character patterns
                if re.search(r'[çğıöşüÇĞİÖŞÜ]', raw_value):
                    language = "tr"
                elif re.search(r'[äöüßÄÖÜ]', raw_value):
                    language = "de"
                else:
                    language = "en"
            
            try:
                # ==============================================================
                # PHONE NUMBER VERIFICATION
                # ==============================================================
                if info_type == "phone":
                    # Step 1: Clean the raw value
                    cleaned = raw_value.strip()
                    
                    # ---- Advanced word-to-number conversion ----
                    # Handles compound numbers: "einunddreißig" → 31, "on iki" → 12
                    
                    def convert_spoken_to_digits(text):
                        """Convert spoken number words to digit strings across TR/DE/EN."""
                        text = text.lower().strip()
                        
                        # === PHASE 1: German compound numbers (einundzwanzig = 21) ===
                        # German says numbers as "ones-and-tens": einunddreißig = 1 + und + 30 = 31
                        de_ones = {
                            "ein": 1, "zwei": 2, "zwo": 2, "drei": 3, "vier": 4,
                            "fünf": 5, "sechs": 6, "sieben": 7, "sieb": 7,
                            "acht": 8, "neun": 9
                        }
                        de_tens = {
                            "zwanzig": 20, "dreißig": 30, "dreissig": 30, "vierzig": 40,
                            "fünfzig": 50, "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90
                        }
                        # Build compound pattern: (ein|zwei|...)und(zwanzig|dreißig|...)
                        de_ones_pattern = "|".join(sorted(de_ones.keys(), key=len, reverse=True))
                        de_tens_pattern = "|".join(sorted(de_tens.keys(), key=len, reverse=True))
                        compound_pattern = re.compile(
                            rf'({de_ones_pattern})und({de_tens_pattern})',
                            re.IGNORECASE
                        )
                        
                        def de_compound_replace(match):
                            ones_word = match.group(1).lower()
                            tens_word = match.group(2).lower()
                            return str(de_ones.get(ones_word, 0) + de_tens.get(tens_word, 0))
                        
                        text = compound_pattern.sub(de_compound_replace, text)
                        
                        # === PHASE 2: Turkish compound numbers (on iki = 12, yirmi üç = 23) ===
                        tr_tens = {
                            "on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50,
                            "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90
                        }
                        tr_ones = {
                            "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5,
                            "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9
                        }
                        # Turkish: tens comes FIRST, then ones (on iki = 12)
                        tr_tens_pattern = "|".join(sorted(tr_tens.keys(), key=len, reverse=True))
                        tr_ones_pattern = "|".join(sorted(tr_ones.keys(), key=len, reverse=True))
                        tr_compound_pattern = re.compile(
                            rf'({tr_tens_pattern})\s+({tr_ones_pattern})',
                            re.IGNORECASE
                        )
                        
                        def tr_compound_replace(match):
                            tens_word = match.group(1).lower()
                            ones_word = match.group(2).lower()
                            return str(tr_tens.get(tens_word, 0) + tr_ones.get(ones_word, 0))
                        
                        text = tr_compound_pattern.sub(tr_compound_replace, text)
                        
                        # === PHASE 3: English compound numbers (twenty three = 23) ===
                        en_tens = {
                            "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
                            "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
                        }
                        en_ones = {
                            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                            "six": 6, "seven": 7, "eight": 8, "nine": 9
                        }
                        en_tens_pattern = "|".join(sorted(en_tens.keys(), key=len, reverse=True))
                        en_ones_pattern = "|".join(sorted(en_ones.keys(), key=len, reverse=True))
                        en_compound_pattern = re.compile(
                            rf'({en_tens_pattern})[\s\-]+({en_ones_pattern})',
                            re.IGNORECASE
                        )
                        
                        def en_compound_replace(match):
                            tens_word = match.group(1).lower()
                            ones_word = match.group(2).lower()
                            return str(en_tens.get(tens_word, 0) + en_ones.get(ones_word, 0))
                        
                        text = en_compound_pattern.sub(en_compound_replace, text)
                        
                        # === PHASE 4: Single word-to-digit mapping (remaining words) ===
                        word_to_digit = {
                            # Turkish single digits
                            "sıfır": "0", "bir": "1", "iki": "2", "üç": "3", "dört": "4",
                            "beş": "5", "altı": "6", "yedi": "7", "sekiz": "8", "dokuz": "9",
                            # Turkish tens (standalone - not already handled as compound)
                            "on": "10", "yirmi": "20", "otuz": "30", "kırk": "40", "elli": "50",
                            "altmış": "60", "yetmiş": "70", "seksen": "80", "doksan": "90",
                            # German single digits
                            "null": "0", "eins": "1", "zwei": "2", "zwo": "2", "drei": "3",
                            "vier": "4", "fünf": "5", "sechs": "6", "sieben": "7", "acht": "8", "neun": "9",
                            # German teens
                            "zehn": "10", "elf": "11", "zwölf": "12", "dreizehn": "13", "vierzehn": "14",
                            "fünfzehn": "15", "sechzehn": "16", "siebzehn": "17", "achtzehn": "18", "neunzehn": "19",
                            # German tens (standalone)
                            "zwanzig": "20", "dreißig": "30", "dreissig": "30", "vierzig": "40",
                            "fünfzig": "50", "sechzig": "60", "siebzig": "70", "achtzig": "80", "neunzig": "90",
                            # English single digits
                            "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
                            "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
                            # English teens
                            "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
                            "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
                            # English tens (standalone)
                            "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
                            "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
                            # Common STT variants / misspellings
                            "nul": "0", "nulle": "0",  # German variants
                            "too": "2", "for": "4", "fore": "4", "ate": "8",  # English homophones
                            "fier": "4", "acht": "8",  # German STT variants
                            "double": "",  # Handled separately below
                            "triple": "",  # Handled separately below
                            # German "hundert" for area codes
                            "hundert": "100",
                        }
                        
                        # Handle "double X" and "triple X" patterns (e.g., "double five" → "55")
                        double_pattern = re.compile(r'double\s+(\w+)', re.IGNORECASE)
                        triple_pattern = re.compile(r'triple\s+(\w+)', re.IGNORECASE)
                        doppel_pattern = re.compile(r'doppel\s+(\w+)', re.IGNORECASE)
                        
                        def expand_double(match):
                            word = match.group(1).lower()
                            digit = word_to_digit.get(word, word)
                            if digit.isdigit():
                                return digit * 2
                            return match.group(0)
                        
                        def expand_triple(match):
                            word = match.group(1).lower()
                            digit = word_to_digit.get(word, word)
                            if digit.isdigit():
                                return digit * 3
                            return match.group(0)
                        
                        text = triple_pattern.sub(expand_triple, text)
                        text = double_pattern.sub(expand_double, text)
                        text = doppel_pattern.sub(expand_double, text)
                        
                        # Replace remaining single words with digits (longest first)
                        for word, digit in sorted(word_to_digit.items(), key=lambda x: -len(x[0])):
                            if digit:  # Skip empty values (double/triple)
                                # Use word boundary matching for accuracy
                                text = re.sub(rf'\b{re.escape(word)}\b', digit, text, flags=re.IGNORECASE)
                        
                        return text
                    
                    # Apply the conversion
                    lower_val = convert_spoken_to_digits(cleaned)
                    
                    # Remove all non-digit and non-+ characters
                    phone_digits = re.sub(r'[^\d+]', '', lower_val)
                    
                    # If starts with 00, convert to +
                    if phone_digits.startswith('00'):
                        phone_digits = '+' + phone_digits[2:]
                    
                    # Turkish specific: 05XX... → +905XX...
                    if not phone_digits.startswith('+'):
                        if phone_digits.startswith('0') and len(phone_digits) == 11:
                            # Turkish mobile: 05XX XXX XX XX → +90 5XX XXX XX XX
                            phone_digits = '+90' + phone_digits[1:]
                        elif phone_digits.startswith('05') and len(phone_digits) == 10:
                            # Missing leading zero: 532... → +90 532...
                            phone_digits = '+90' + phone_digits[1:]
                    
                    # German specific: 0172... → +49172...
                    if language == "de" and phone_digits.startswith('0') and not phone_digits.startswith('+'):
                        phone_digits = '+49' + phone_digits[1:]
                    
                    # US/UK specific
                    if language == "en" and not phone_digits.startswith('+'):
                        if len(phone_digits) == 10:  # US without country code
                            phone_digits = '+1' + phone_digits
                        elif len(phone_digits) == 11 and phone_digits.startswith('1'):
                            phone_digits = '+' + phone_digits
                    
                    # Validate using phonenumbers library
                    try:
                        import phonenumbers
                        
                        # Try parsing with country hint based on language
                        default_region = {"tr": "TR", "de": "DE", "en": "US"}.get(language, "TR")
                        parsed = phonenumbers.parse(phone_digits, default_region)
                        
                        is_valid = phonenumbers.is_valid_number(parsed)
                        is_possible = phonenumbers.is_possible_number(parsed)
                        number_type = phonenumbers.number_type(parsed)
                        
                        # Format in international and national formats
                        formatted_intl = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                        formatted_national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
                        formatted_e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                        
                        country_code = phonenumbers.region_code_for_number(parsed)
                        
                        # Number type descriptions
                        type_names = {
                            0: "fixed_line", 1: "mobile", 2: "fixed_line_or_mobile",
                            3: "toll_free", 4: "premium_rate", 5: "shared_cost",
                            6: "voip", 7: "personal_number", 10: "unknown"
                        }
                        phone_type = type_names.get(number_type, "unknown")
                        
                        if is_valid:
                            messages = {
                                "tr": f"✅ Telefon numarası geçerli: {formatted_intl}. Bu numarayı kaydedebilirsin.",
                                "de": f"✅ Telefonnummer gültig: {formatted_intl}. Sie können diese Nummer speichern.",
                                "en": f"✅ Phone number valid: {formatted_intl}. You can save this number."
                            }
                            return {
                                "success": True,
                                "valid": True,
                                "info_type": "phone",
                                "original": raw_value,
                                "normalized": formatted_e164,
                                "formatted": formatted_intl,
                                "formatted_national": formatted_national,
                                "country_code": country_code,
                                "phone_type": phone_type,
                                "digit_count": len(re.sub(r'\D', '', formatted_e164)),
                                "message": messages.get(language, messages["en"])
                            }
                        elif is_possible:
                            messages = {
                                "tr": f"⚠️ Numara olası ama kesin değil: {formatted_intl}. Müşteriden tekrar teyit al.",
                                "de": f"⚠️ Nummer möglich aber unsicher: {formatted_intl}. Bitte nochmals bestätigen.",
                                "en": f"⚠️ Number possible but uncertain: {formatted_intl}. Please confirm again."
                            }
                            return {
                                "success": True,
                                "valid": False,
                                "possible": True,
                                "info_type": "phone",
                                "original": raw_value,
                                "normalized": formatted_e164,
                                "formatted": formatted_intl,
                                "country_code": country_code,
                                "message": messages.get(language, messages["en"])
                            }
                        else:
                            messages = {
                                "tr": f"❌ Geçersiz telefon numarası: '{raw_value}'. Müşteriden tekrar sor. Numara {len(phone_digits)} hane, doğru hane sayısı mı?",
                                "de": f"❌ Ungültige Telefonnummer: '{raw_value}'. Bitte erneut fragen. Nummer hat {len(phone_digits)} Stellen.",
                                "en": f"❌ Invalid phone number: '{raw_value}'. Please ask again. Number has {len(phone_digits)} digits."
                            }
                            return {
                                "success": True,
                                "valid": False,
                                "possible": False,
                                "info_type": "phone",
                                "original": raw_value,
                                "digits_found": phone_digits,
                                "digit_count": len(phone_digits),
                                "message": messages.get(language, messages["en"])
                            }
                    except Exception as phone_err:
                        messages = {
                            "tr": f"❌ Telefon numarası ayrıştırılamadı: '{raw_value}'. Hata: {str(phone_err)}. Lütfen müşteriden tekrar isteyin.",
                            "de": f"❌ Telefonnummer konnte nicht analysiert werden: '{raw_value}'. Bitte erneut fragen.",
                            "en": f"❌ Could not parse phone number: '{raw_value}'. Please ask again."
                        }
                        return {
                            "success": True,
                            "valid": False,
                            "info_type": "phone",
                            "original": raw_value,
                            "digits_found": phone_digits,
                            "error": str(phone_err),
                            "message": messages.get(language, messages["en"])
                        }
                
                # ==============================================================
                # EMAIL VERIFICATION
                # ==============================================================
                elif info_type == "email":
                    # Step 1: Normalize spoken variants to actual characters
                    email = raw_value.lower().strip()
                    
                    # @ symbol variants (TR/DE/EN) - most comprehensive list
                    at_variants = [
                        # Turkish (longest first to avoid partial match)
                        "maymun işareti", "alt çizgi işareti",
                        "et işareti", "at işareti", "kuyruklu a",
                        "a işareti", "güzel a", "özel a", "salyangoz",
                        "et", "kuyruklu",
                        # German
                        "affenschaukel", "affenschwanz", "klammeraffe",
                        "affenohr", "at-zeichen", "at zeichen",
                        # English
                        "at the rate", "at symbol", "at sign",
                        # Universal (last - shortest)
                        "at",
                    ]
                    # Sort by length (longest first) to avoid partial replacements
                    for variant in sorted(at_variants, key=len, reverse=True):
                        email = email.replace(variant, "@")
                    
                    # Dot variants
                    dot_variants = [
                        "nokta", "punto",  # TR
                        "punkt",           # DE
                        "dot", "period", "point",  # EN
                    ]
                    for variant in sorted(dot_variants, key=len, reverse=True):
                        email = email.replace(f" {variant} ", ".")
                        email = email.replace(f"{variant} ", ".")
                        email = email.replace(f" {variant}", ".")
                    
                    # Dash variants
                    dash_variants = [
                        "kısa çizgi", "çizgi", "tire",  # TR
                        "bindestrich", "minus", "strich",  # DE
                        "hyphen", "dash",  # EN
                    ]
                    for variant in sorted(dash_variants, key=len, reverse=True):
                        email = email.replace(f" {variant} ", "-")
                        email = email.replace(f"{variant} ", "-")
                        email = email.replace(f" {variant}", "-")
                    
                    # Underscore variants
                    underscore_variants = [
                        "alt çizgi işareti", "alt çizgi", "alt tire",  # TR
                        "unterstreichung", "unterstrich", "bodenstrich",  # DE
                        "underscore", "underline", "low dash",  # EN
                    ]
                    for variant in sorted(underscore_variants, key=len, reverse=True):
                        email = email.replace(f" {variant} ", "_")
                        email = email.replace(f"{variant} ", "_")
                        email = email.replace(f" {variant}", "_")
                    
                    # ---- Convert umlauts and special chars to ASCII for email ----
                    # German umlauts: ä→ae, ö→oe, ü→ue, ß→ss
                    umlaut_map = {
                        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                        "Ä": "ae", "Ö": "oe", "Ü": "ue",
                        # Turkish special chars
                        "ç": "c", "ğ": "g", "ı": "i", "ş": "s",
                        "Ç": "c", "Ğ": "g", "İ": "i", "Ş": "s",
                        # Common diacritics
                        "é": "e", "è": "e", "ê": "e", "ë": "e",
                        "á": "a", "à": "a", "â": "a",
                        "ó": "o", "ò": "o", "ô": "o",
                        "ú": "u", "ù": "u", "û": "u",
                        "ñ": "n", "ý": "y",
                    }
                    for char, replacement in umlaut_map.items():
                        email = email.replace(char, replacement)
                    
                    # Remove remaining spaces (from spelling: "a l i" → "ali")
                    # But preserve @ and . positions
                    parts = email.split("@")
                    if len(parts) == 2:
                        local_part = parts[0].replace(" ", "")
                        domain_part = parts[1].replace(" ", "")
                        email = f"{local_part}@{domain_part}"
                    elif len(parts) > 2:
                        # Multiple @ found - keep only first, merge rest
                        local_part = parts[0].replace(" ", "")
                        domain_part = "".join(parts[1:]).replace(" ", "")
                        email = f"{local_part}@{domain_part}"
                    else:
                        email = email.replace(" ", "")
                    
                    # Common domain corrections (comprehensive)
                    domain_corrections = {
                        # Gmail variants
                        "gmailcom": "gmail.com", "gmailpunktcom": "gmail.com",
                        "gmailnoktacom": "gmail.com", "gmaildotcom": "gmail.com",
                        "gmal": "gmail.com", "gmial": "gmail.com", "gamil": "gmail.com",
                        "gmail": "gmail.com",
                        # Hotmail/Outlook
                        "hotmailcom": "hotmail.com", "hotmailpunktcom": "hotmail.com",
                        "hotmail": "hotmail.com",
                        "outlookcom": "outlook.com", "outlookde": "outlook.de",
                        "outlook": "outlook.com",
                        # Yahoo
                        "yahoocom": "yahoo.com", "yahoode": "yahoo.de",
                        "yahoo": "yahoo.com",
                        # German providers
                        "gmxde": "gmx.de", "gmxnet": "gmx.net", "gmxcom": "gmx.com",
                        "gmx": "gmx.de",
                        "webde": "web.de", "web": "web.de",
                        "tonlinede": "t-online.de", "t-onlinede": "t-online.de",
                        "tonline": "t-online.de", "t-online": "t-online.de",
                        "freenetde": "freenet.de", "freenet": "freenet.de",
                        "posteode": "posteo.de", "posteo": "posteo.de",
                        "mailboxorg": "mailbox.org", "mailbox": "mailbox.org",
                        "arcorde": "arcor.de", "arcor": "arcor.de",
                        "1und1de": "1und1.de", "1und1": "1und1.de",
                        # iCloud
                        "icloudcom": "icloud.com", "icloud": "icloud.com",
                        # Yandex
                        "yandexcom": "yandex.com", "yandex": "yandex.com",
                        # ProtonMail
                        "protonmailcom": "protonmail.com", "protonmail": "protonmail.com",
                        "protonme": "proton.me", "proton": "proton.me",
                        # Turkish providers
                        "comtr": ".com.tr",
                    }
                    
                    if "@" in email:
                        local, domain = email.split("@", 1)
                        domain_clean = domain.replace(".", "").replace(" ", "").replace("-", "")
                        
                        # Try exact match first
                        if domain_clean in domain_corrections:
                            domain = domain_corrections[domain_clean]
                        else:
                            # Try with dots removed but hyphens kept
                            domain_with_hyphen = domain.replace(".", "").replace(" ", "")
                            if domain_with_hyphen in domain_corrections:
                                domain = domain_corrections[domain_with_hyphen]
                            # Ensure domain has at least one dot
                            elif "." not in domain:
                                # Check if domain matches a known provider name
                                if domain in domain_corrections:
                                    domain = domain_corrections[domain]
                                else:
                                    # Try common TLDs based on language
                                    tld_priority = {
                                        "de": [".de", ".com", ".net", ".org"],
                                        "tr": [".com.tr", ".com", ".net", ".org"],
                                        "en": [".com", ".net", ".org", ".co.uk"]
                                    }.get(language, [".com", ".de", ".net", ".org"])
                                    for tld in tld_priority:
                                        domain = domain + tld
                                        break
                        
                        # Fix common STT errors in domain
                        domain = domain.replace(" dot ", ".").replace(" punkt ", ".").replace(" nokta ", ".")
                        
                        email = f"{local}@{domain}"
                    
                    # Validate email format with regex
                    email_regex = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
                    is_valid = bool(re.match(email_regex, email))
                    
                    # Check for common issues
                    issues = []
                    if "@" not in email:
                        issues.append({
                            "tr": "@ işareti bulunamadı",
                            "de": "@ Zeichen fehlt",
                            "en": "@ symbol not found"
                        })
                    elif email.count("@") > 1:
                        issues.append({
                            "tr": "Birden fazla @ işareti var",
                            "de": "Mehrere @ Zeichen gefunden",
                            "en": "Multiple @ symbols found"
                        })
                    if not re.search(r'\.[a-zA-Z]{2,}$', email):
                        issues.append({
                            "tr": "Geçersiz domain uzantısı (.com, .de, .net vb. olmalı)",
                            "de": "Ungültige Domain-Endung (sollte .com, .de, .net etc. sein)",
                            "en": "Invalid domain extension (should be .com, .de, .net etc.)"
                        })
                    # Check for remaining non-ASCII after umlaut conversion
                    if re.search(r'[^\x00-\x7F]', email):
                        issues.append({
                            "tr": "E-postada hala özel karakter var - ASCII karakter kullanılmalı",
                            "de": "E-Mail enthält noch Sonderzeichen - ASCII-Zeichen verwenden",
                            "en": "Email still contains special characters - use ASCII only"
                        })
                    # Check for consecutive dots
                    if ".." in email:
                        issues.append({
                            "tr": "Ardışık nokta bulundu",
                            "de": "Aufeinanderfolgende Punkte gefunden",
                            "en": "Consecutive dots found"
                        })
                    # Check local part starts/ends with dot
                    if "@" in email:
                        local_check = email.split("@")[0]
                        if local_check.startswith(".") or local_check.endswith("."):
                            issues.append({
                                "tr": "Kullanıcı adı nokta ile başlayamaz/bitemez",
                                "de": "Benutzername darf nicht mit Punkt beginnen/enden",
                                "en": "Username cannot start/end with dot"
                            })
                    
                    if is_valid and not issues:
                        messages = {
                            "tr": f"✅ E-posta adresi geçerli: {email}. Bu adresi kaydedebilirsin.",
                            "de": f"✅ E-Mail-Adresse gültig: {email}. Sie können diese speichern.",
                            "en": f"✅ Email address valid: {email}. You can save this."
                        }
                        return {
                            "success": True,
                            "valid": True,
                            "info_type": "email",
                            "original": raw_value,
                            "normalized": email,
                            "local_part": email.split("@")[0] if "@" in email else "",
                            "domain": email.split("@")[1] if "@" in email else "",
                            "message": messages.get(language, messages["en"])
                        }
                    else:
                        issue_msgs = [i.get(language, i.get("en", "")) for i in issues]
                        messages = {
                            "tr": f"❌ E-posta formatı hatalı: '{email}'. Sorunlar: {'; '.join(issue_msgs)}. Müşteriden tekrar sor.",
                            "de": f"❌ E-Mail-Format ungültig: '{email}'. Probleme: {'; '.join(issue_msgs)}. Bitte erneut fragen.",
                            "en": f"❌ Email format invalid: '{email}'. Issues: {'; '.join(issue_msgs)}. Please ask again."
                        }
                        return {
                            "success": True,
                            "valid": False,
                            "info_type": "email",
                            "original": raw_value,
                            "normalized": email,
                            "issues": issue_msgs,
                            "message": messages.get(language, messages["en"])
                        }
                
                # ==============================================================
                # ADDRESS VERIFICATION
                # ==============================================================
                elif info_type == "address":
                    address = raw_value.strip()
                    
                    # Basic address validation
                    issues = []
                    components_found = {}
                    
                    # Check minimum length
                    if len(address) < 10:
                        issues.append({
                            "tr": "Adres çok kısa, eksik bilgi olabilir",
                            "de": "Adresse zu kurz, möglicherweise unvollständig",
                            "en": "Address too short, may be incomplete"
                        })
                    
                    # Turkish address patterns
                    if language == "tr":
                        # Check for common Turkish address components
                        has_district = bool(re.search(r'(mah|mahalle|mahallesi|köy|köyü)', address.lower()))
                        has_street = bool(re.search(r'(cad|cadde|caddesi|sok|sokak|sokağı|bulvar|bulvarı|meydan|meydanı)', address.lower()))
                        has_number = bool(re.search(r'(no|numara|no:|no\.|daire|kat|d:|k:|no\s*\d|bina)', address.lower()))
                        
                        # All 81 provinces of Turkey (major ones)
                        tr_cities = [
                            "istanbul", "ankara", "izmir", "bursa", "antalya", "adana", "konya",
                            "gaziantep", "mersin", "diyarbakır", "kocaeli", "samsun", "denizli",
                            "eskişehir", "trabzon", "malatya", "erzurum", "van", "şanlıurfa",
                            "kayseri", "hatay", "manisa", "balıkesir", "kahramanmaraş", "aydın",
                            "tekirdağ", "sakarya", "muğla", "mardin", "ordu", "sivas", "elazığ",
                            "düzce", "afyon", "afyonkarahisar", "tokat", "giresun", "çorum",
                            "aksaray", "edirne", "yozgat", "ağrı", "rize", "kırklareli", "bolu",
                            "amasya", "niğde", "nevşehir", "kastamonu", "batman", "siirt",
                            "zonguldak", "çanakkale", "artvin", "burdur", "karaman", "kırıkkale",
                            "bitlis", "erzincan", "sinop", "muş", "iğdır", "kilis", "adıyaman",
                            "osmaniye", "tunceli", "ardahan", "hakkari", "bayburt", "bartın",
                            "isparta", "uşak", "çankırı", "karabük", "bilecik", "kütahya",
                            "yalova", "şırnak", "gümüşhane"
                        ]
                        has_city = any(city in address.lower() for city in tr_cities)
                        
                        # Turkish postal code: 5 digits, starting with 01-81
                        has_postal = bool(re.search(r'\b(0[1-9]|[1-7]\d|8[01])\d{3}\b', address))
                        
                        components_found = {
                            "mahalle": has_district,
                            "sokak/cadde": has_street,
                            "numara": has_number,
                            "şehir": has_city,
                            "posta_kodu": has_postal
                        }
                        
                        if not has_street and not has_district:
                            issues.append({"tr": "Sokak/cadde veya mahalle bilgisi eksik", "de": "Straße oder Viertel fehlt", "en": "Street or neighborhood missing"})
                        if not has_number:
                            issues.append({"tr": "Bina/daire numarası eksik", "de": "Hausnummer fehlt", "en": "Building/apartment number missing"})
                    
                    # German address patterns
                    elif language == "de":
                        # Street types: straße, weg, gasse, platz, allee, ring, damm, ufer, chaussee, steig, pfad, zeile, graben, markt
                        has_street = bool(re.search(
                            r'(stra(?:ß|ss)e|str\.|weg|gasse|platz|allee|ring|damm|ufer|chaussee|steig|pfad|zeile|graben|markt|promenade|stieg)',
                            address.lower()
                        ))
                        # Hausnummer: digit(s) optionally followed by a letter (e.g., 12a, 5b)
                        has_hausnummer = bool(re.search(r'\b\d{1,4}[a-zA-Z]?\b', address))
                        # PLZ: exactly 5 digits, valid range 01000-99999
                        plz_match = re.search(r'\b(\d{5})\b', address)
                        has_plz = False
                        plz_value = None
                        if plz_match:
                            plz_value = plz_match.group(1)
                            # Valid German PLZ: 01000-99999 (no 00xxx)
                            has_plz = 1000 <= int(plz_value) <= 99999
                        
                        # Major German cities (top 80+)
                        de_cities = [
                            "berlin", "hamburg", "münchen", "muenchen", "köln", "koeln",
                            "frankfurt", "stuttgart", "düsseldorf", "duesseldorf", "dortmund",
                            "essen", "leipzig", "bremen", "dresden", "hannover", "nürnberg",
                            "nuernberg", "duisburg", "bochum", "wuppertal", "bielefeld", "bonn",
                            "münster", "muenster", "karlsruhe", "mannheim", "augsburg", "wiesbaden",
                            "gelsenkirchen", "mönchengladbach", "braunschweig", "chemnitz", "kiel",
                            "aachen", "halle", "magdeburg", "freiburg", "krefeld", "lübeck",
                            "oberhausen", "erfurt", "mainz", "rostock", "kassel", "hagen",
                            "hamm", "saarbrücken", "mülheim", "potsdam", "ludwigshafen",
                            "oldenburg", "leverkusen", "osnabrück", "solingen", "heidelberg",
                            "herne", "neuss", "darmstadt", "paderborn", "regensburg", "ingolstadt",
                            "würzburg", "wolfsburg", "ulm", "göttingen", "heilbronn", "pforzheim",
                            "offenbach", "recklinghausen", "bottrop", "trier", "bremerhaven",
                            "reutlingen", "remscheid", "koblenz", "bergisch gladbach", "jena",
                            "erlangen", "moers", "siegen", "konstanz", "hildesheim", "salzgitter"
                        ]
                        has_city = any(city in address.lower() for city in de_cities)
                        
                        # PLZ-City mapping hints for validation
                        plz_city_hints = {
                            "10": "berlin", "12": "berlin", "13": "berlin", "14": "berlin",
                            "20": "hamburg", "21": "hamburg", "22": "hamburg",
                            "80": "münchen", "81": "münchen",
                            "50": "köln", "51": "köln",
                            "60": "frankfurt", "65": "wiesbaden",
                            "70": "stuttgart",
                            "40": "düsseldorf",
                            "44": "dortmund",
                            "45": "essen",
                            "04": "leipzig",
                            "28": "bremen",
                            "01": "dresden",
                            "30": "hannover", "31": "hannover",
                            "90": "nürnberg",
                        }
                        
                        # Adresszusatz patterns (c/o, OG, EG, etc.)
                        has_zusatz = bool(re.search(
                            r'(c/o|bei|etage|\d+\.\s*(og|obergeschoss|ug|untergeschoss|eg|erdgeschoss|dg|dachgeschoss)|wohnung|whg|apt)',
                            address.lower()
                        ))
                        
                        components_found = {
                            "straße": has_street,
                            "hausnummer": has_hausnummer,
                            "plz": has_plz,
                            "stadt": has_city,
                            "zusatz": has_zusatz
                        }
                        
                        if not has_street:
                            issues.append({"tr": "Sokak adı eksik", "de": "Straßenname fehlt", "en": "Street name missing"})
                        if not has_hausnummer:
                            issues.append({"tr": "Ev numarası eksik", "de": "Hausnummer fehlt", "en": "House number missing"})
                        if not has_plz:
                            issues.append({"tr": "Posta kodu eksik (5 haneli)", "de": "Postleitzahl fehlt (5-stellig)", "en": "Postal code missing (5 digits)"})
                        if not has_city:
                            issues.append({"tr": "Şehir adı eksik", "de": "Stadtname fehlt", "en": "City name missing"})
                        
                        # PLZ-City consistency check
                        if has_plz and has_city and plz_value:
                            plz_prefix = plz_value[:2]
                            expected_city = plz_city_hints.get(plz_prefix)
                            if expected_city:
                                addr_lower = address.lower()
                                if expected_city not in addr_lower:
                                    # Warn about possible mismatch (not an error, just info)
                                    components_found["plz_city_hint"] = f"PLZ {plz_value} is typically for {expected_city.title()} area"
                    
                    # English address patterns
                    elif language == "en":
                        has_number = bool(re.search(r'\d+', address))
                        has_street = bool(re.search(
                            r'(street|st\.|avenue|ave\.|road|rd\.|drive|dr\.|lane|ln\.|boulevard|blvd\.|way|place|pl\.|court|ct\.|circle|terrace|trail|pike|highway|hwy)',
                            address.lower()
                        ))
                        has_zip = bool(re.search(r'\b\d{5}(-\d{4})?\b', address))  # US ZIP
                        has_state = bool(re.search(
                            r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b',
                            address
                        ))
                        
                        components_found = {
                            "number": has_number,
                            "street": has_street,
                            "zip": has_zip,
                            "state": has_state
                        }
                        
                        if not has_number:
                            issues.append({"tr": "Numara eksik", "de": "Nummer fehlt", "en": "Number missing"})
                        if not has_street:
                            issues.append({"tr": "Sokak tipi eksik", "de": "Straßentyp fehlt", "en": "Street type missing"})
                    
                    # Normalize address
                    normalized = address
                    # Smart capitalization - preserve abbreviations and handle German conventions
                    keep_lower = {"c/o", "bei", "und", "an", "der", "die", "das", "am", "im", "in", "von", "vom", "zum", "zur"}
                    keep_upper = {"PLZ", "OG", "EG", "UG", "DG", "NRW", "BW"}
                    words = normalized.split()
                    norm_words = []
                    for i, word in enumerate(words):
                        if word.upper() in keep_upper:
                            norm_words.append(word.upper())
                        elif word.lower() in keep_lower and i > 0:
                            norm_words.append(word.lower())
                        elif not word.isupper():
                            norm_words.append(word.capitalize())
                        else:
                            norm_words.append(word)
                    normalized = ' '.join(norm_words)
                    
                    if not issues:
                        messages = {
                            "tr": f"✅ Adres geçerli görünüyor: {normalized}. Bu adresi kaydedebilirsin.",
                            "de": f"✅ Adresse scheint gültig: {normalized}. Sie können diese speichern.",
                            "en": f"✅ Address looks valid: {normalized}. You can save this."
                        }
                        return {
                            "success": True,
                            "valid": True,
                            "info_type": "address",
                            "original": raw_value,
                            "normalized": normalized,
                            "components": components_found,
                            "message": messages.get(language, messages["en"])
                        }
                    else:
                        issue_msgs = [i.get(language, i.get("en", "")) for i in issues]
                        messages = {
                            "tr": f"⚠️ Adres eksik olabilir: {'; '.join(issue_msgs)}. Eksik bilgileri müşteriden sor.",
                            "de": f"⚠️ Adresse möglicherweise unvollständig: {'; '.join(issue_msgs)}. Bitte fehlende Angaben erfragen.",
                            "en": f"⚠️ Address may be incomplete: {'; '.join(issue_msgs)}. Please ask for missing details."
                        }
                        return {
                            "success": True,
                            "valid": False,
                            "info_type": "address",
                            "original": raw_value,
                            "normalized": normalized,
                            "components": components_found,
                            "issues": issue_msgs,
                            "message": messages.get(language, messages["en"])
                        }
                
                # ==============================================================
                # NAME VERIFICATION
                # ==============================================================
                elif info_type == "name":
                    name = raw_value.strip()
                    
                    issues = []
                    
                    # Check minimum parts (first + last name)
                    name_parts = name.split()
                    if len(name_parts) < 2:
                        issues.append({
                            "tr": "Ad ve soyad birlikte gerekli",
                            "de": "Vor- und Nachname erforderlich",
                            "en": "First and last name required"
                        })
                    
                    # Check for numbers in name
                    if re.search(r'\d', name):
                        issues.append({
                            "tr": "İsimde rakam bulundu",
                            "de": "Zahlen im Namen gefunden",
                            "en": "Numbers found in name"
                        })
                    
                    # Check for special characters (allow Turkish, German, common diacritics, hyphens for double names)
                    if re.search(r'[!@#$%^&*()+=\[\]{};:"|<>?/\\~`]', name):
                        issues.append({
                            "tr": "İsimde özel karakter bulundu",
                            "de": "Sonderzeichen im Namen gefunden",
                            "en": "Special characters found in name"
                        })
                    
                    # Allowed short parts: titles, prefixes, initials
                    allowed_short = {
                        "dr", "prof", "mr", "mrs", "ms", "jr", "sr",
                        "von", "van", "de", "el", "al", "zu", "zum", "zur",
                        "ten", "ter", "op", "in", "am",
                        "di", "du", "da", "la", "le", "do",
                    }
                    # Check for very short parts (but allow single-letter initials like "J." or "M.")
                    for part in name_parts:
                        clean_part = part.rstrip(".")
                        if len(clean_part) < 2 and clean_part.lower() not in allowed_short:
                            # Allow single letter if it's an initial (followed by period)
                            if not part.endswith("."):
                                issues.append({
                                    "tr": f"İsim parçası çok kısa: '{part}', heceleme gerekebilir",
                                    "de": f"Namensteil sehr kurz: '{part}', Buchstabieren empfohlen",
                                    "en": f"Name part very short: '{part}', spelling may be needed"
                                })
                                break
                    
                    # Normalize: capitalize first letter of each part, handle special cases
                    normalized_parts = []
                    lower_prefixes = {
                        "von", "van", "de", "del", "della", "di", "du", "la", "le",
                        "el", "al", "bin", "bint", "zu", "zum", "zur", "ten", "ter",
                        "op", "in", "am", "auf", "und"
                    }
                    # Academic titles to preserve format
                    title_formats = {
                        "dr": "Dr.", "dr.": "Dr.", "prof": "Prof.", "prof.": "Prof.",
                        "dipl": "Dipl.", "dipl.": "Dipl.", "ing": "Ing.", "ing.": "Ing.",
                        "mag": "Mag.", "mag.": "Mag.",
                    }
                    
                    for i, part in enumerate(name_parts):
                        lower_part = part.lower().rstrip(".")
                        
                        # Handle academic titles
                        if lower_part in title_formats:
                            normalized_parts.append(title_formats[lower_part])
                        # Handle lowercase prefixes (not at beginning of name)
                        elif part.lower() in lower_prefixes and i > 0:
                            normalized_parts.append(part.lower())
                        # Handle hyphenated double names (Hans-Peter, Anna-Maria)
                        elif "-" in part:
                            hyphen_parts = part.split("-")
                            normalized_parts.append("-".join(
                                p.capitalize() for p in hyphen_parts
                            ))
                        # Handle initials (J., M.)
                        elif len(part) <= 2 and part.endswith("."):
                            normalized_parts.append(part.upper())
                        else:
                            normalized_parts.append(part.capitalize())
                    
                    normalized = " ".join(normalized_parts)
                    
                    if not issues:
                        messages = {
                            "tr": f"✅ İsim geçerli: {normalized}. Bu ismi kaydedebilirsin.",
                            "de": f"✅ Name gültig: {normalized}. Sie können diesen speichern.",
                            "en": f"✅ Name valid: {normalized}. You can save this."
                        }
                        return {
                            "success": True,
                            "valid": True,
                            "info_type": "name",
                            "original": raw_value,
                            "normalized": normalized,
                            "first_name": normalized_parts[0] if normalized_parts else "",
                            "last_name": " ".join(normalized_parts[1:]) if len(normalized_parts) > 1 else "",
                            "message": messages.get(language, messages["en"])
                        }
                    else:
                        issue_msgs = [i.get(language, i.get("en", "")) for i in issues]
                        messages = {
                            "tr": f"⚠️ İsim kontrol: {'; '.join(issue_msgs)}. Müşteriden teyit al.",
                            "de": f"⚠️ Namensüberprüfung: {'; '.join(issue_msgs)}. Bitte bestätigen.",
                            "en": f"⚠️ Name check: {'; '.join(issue_msgs)}. Please confirm."
                        }
                        return {
                            "success": True,
                            "valid": False,
                            "info_type": "name",
                            "original": raw_value,
                            "normalized": normalized,
                            "issues": issue_msgs,
                            "message": messages.get(language, messages["en"])
                        }
                
                else:
                    return {
                        "success": False,
                        "error": "unknown_type",
                        "message": f"Unknown info_type: {info_type}. Use: phone, email, address, name"
                    }
                    
            except Exception as e:
                logger.error(f"verify_contact_info error: {e}", exc_info=True)
                return {
                    "success": False,
                    "info_type": info_type,
                    "original": raw_value,
                    "message": {
                        "tr": "Doğrulama sırasında hata oluştu. Bilgiyi tekrar alın.",
                        "de": "Fehler bei der Überprüfung. Bitte erneut erfassen.",
                        "en": "Verification failed. Please capture the info again."
                    }.get(language, "Verification failed. Please capture the info again.")
                }
        
        elif name == "submit_survey_answer":
            # Handle survey answer submission
            question_id = args.get("question_id", "")
            answer = args.get("answer", "")
            answer_value = args.get("answer_value")
            
            if not question_id or not answer:
                return {
                    "success": False,
                    "message": "Soru ID ve cevap gereklidir"
                }
            
            try:
                from datetime import datetime as dt
                from app.models.models import SurveyResponse, SurveyStatus
                from app.core.database import SessionLocal
                
                agent_id = session.agent_config.get("agent_id")
                call_id = session.agent_config.get("call_id")
                campaign_id = session.agent_config.get("campaign_id")
                survey_config = session.agent_config.get("survey_config", {})
                
                # Get survey questions
                questions = survey_config.get("questions", [])
                question_map = {q.get("id"): q for q in questions}
                current_question = question_map.get(question_id)
                
                if not current_question:
                    return {
                        "success": False,
                        "message": f"Question not found: {question_id}"
                    }
                
                with SessionLocal() as db:
                    # Find or create survey response
                    survey_response = db.query(SurveyResponse).filter(
                        SurveyResponse.call_id == call_id,
                        SurveyResponse.agent_id == agent_id
                    ).first()
                    
                    if not survey_response:
                        survey_response = SurveyResponse(
                            call_id=call_id,
                            agent_id=agent_id,
                            campaign_id=campaign_id,
                            respondent_phone=session.agent_config.get("customer_phone"),
                            respondent_name=session.agent_config.get("customer_name"),
                            status=SurveyStatus.IN_PROGRESS,
                            answers=[],
                            total_questions=len(questions),
                            started_at=dt.utcnow()
                        )
                        db.add(survey_response)
                    
                    # Add answer
                    answers = survey_response.answers or []
                    answers.append({
                        "question_id": question_id,
                        "question_text": current_question.get("text", ""),
                        "question_type": current_question.get("type", ""),
                        "answer": answer,
                        "answer_value": answer_value,
                        "answered_at": dt.utcnow().isoformat()
                    })
                    survey_response.answers = answers
                    survey_response.questions_answered = len(answers)
                    survey_response.current_question_id = question_id
                    
                    # Determine next question based on answer and branching logic
                    next_question_id = None
                    question_type = current_question.get("type", "")
                    
                    if question_type == "yes_no":
                        if answer.lower() in ["yes", "evet", "true", "1"]:
                            next_question_id = current_question.get("next_on_yes")
                        else:
                            next_question_id = current_question.get("next_on_no")
                    elif question_type == "multiple_choice":
                        # Check option-based branching
                        next_by_option = current_question.get("next_by_option", {})
                        if next_by_option and answer in next_by_option:
                            next_question_id = next_by_option[answer]
                        else:
                            next_question_id = current_question.get("next")
                    elif question_type == "rating":
                        # Check range-based branching
                        next_by_range = current_question.get("next_by_range", [])
                        if next_by_range and answer_value is not None:
                            for range_config in next_by_range:
                                if range_config.get("min", 0) <= answer_value <= range_config.get("max", 10):
                                    next_question_id = range_config.get("next")
                                    break
                        if not next_question_id:
                            next_question_id = current_question.get("next")
                    else:
                        next_question_id = current_question.get("next")
                    
                    # Check if survey is complete
                    survey_complete = next_question_id is None
                    
                    if survey_complete:
                        survey_response.status = SurveyStatus.COMPLETED
                        survey_response.completed_at = dt.utcnow()
                        if survey_response.started_at:
                            survey_response.duration_seconds = int(
                                (dt.utcnow() - survey_response.started_at).total_seconds()
                            )
                    
                    db.commit()
                    
                    # Prepare response
                    next_question = question_map.get(next_question_id) if next_question_id else None
                    completion_message = survey_config.get("completion_message", "Thank you for participating in our survey!")
                    show_progress = survey_config.get("show_progress", True)
                    
                    if survey_complete:
                        return {
                            "success": True,
                            "message": "Answer recorded. Survey completed.",
                            "survey_complete": True,
                            "completion_message": completion_message,
                            "total_answered": len(answers),
                            "total_questions": len(questions)
                        }
                    else:
                        progress_text = ""
                        if show_progress:
                            progress_text = f" ({len(answers) + 1}/{len(questions)} questions)"
                        
                        # Format next question based on type
                        next_q_text = next_question.get("text", "")
                        next_q_type = next_question.get("type", "")
                        
                        if next_q_type == "multiple_choice":
                            options = next_question.get("options", [])
                            options_text = ", ".join(options)
                            next_q_text += f" Options: {options_text}"
                        elif next_q_type == "rating":
                            min_val = next_question.get("min_value", 1)
                            max_val = next_question.get("max_value", 10)
                            next_q_text += f" (rate {min_val}-{max_val})"
                        
                        return {
                            "success": True,
                            "message": "Answer recorded.",
                            "survey_complete": False,
                            "next_question": {
                                "id": next_question_id,
                                "type": next_q_type,
                                "text": next_q_text + progress_text,
                                "options": next_question.get("options") if next_q_type == "multiple_choice" else None,
                                "min_value": next_question.get("min_value") if next_q_type == "rating" else None,
                                "max_value": next_question.get("max_value") if next_q_type == "rating" else None
                            },
                            "answered": len(answers),
                            "total": len(questions)
                        }
                        
            except Exception as e:
                logger.error(f"Survey answer error: {e}")
                return {
                    "success": False,
                    "message": "Failed to save survey answer"
                }
        
        elif name == "survey_control":
            # Handle survey start/abort
            action = args.get("action", "")
            reason = args.get("reason", "")
            
            try:
                from datetime import datetime as dt
                from app.models.models import SurveyResponse, SurveyStatus
                from app.core.database import SessionLocal
                
                agent_id = session.agent_config.get("agent_id")
                call_id = session.agent_config.get("call_id")
                campaign_id = session.agent_config.get("campaign_id")
                survey_config = session.agent_config.get("survey_config", {})
                questions = survey_config.get("questions", [])
                
                with SessionLocal() as db:
                    if action == "start":
                        # Start new survey
                        survey_response = SurveyResponse(
                            call_id=call_id,
                            agent_id=agent_id,
                            campaign_id=campaign_id,
                            respondent_phone=session.agent_config.get("customer_phone"),
                            respondent_name=session.agent_config.get("customer_name"),
                            status=SurveyStatus.IN_PROGRESS,
                            answers=[],
                            total_questions=len(questions),
                            started_at=dt.utcnow()
                        )
                        db.add(survey_response)
                        db.commit()
                        
                        # Get first question
                        start_question_id = survey_config.get("start_question") or (questions[0].get("id") if questions else None)
                        first_question = next((q for q in questions if q.get("id") == start_question_id), None)
                        
                        if not first_question:
                            return {
                                "success": False,
                                "message": "Survey questions not found"
                            }
                        
                        # Format first question
                        q_text = first_question.get("text", "")
                        q_type = first_question.get("type", "")
                        
                        if q_type == "multiple_choice":
                            options = first_question.get("options", [])
                            options_text = ", ".join(options)
                            q_text += f" Options: {options_text}"
                        elif q_type == "rating":
                            min_val = first_question.get("min_value", 1)
                            max_val = first_question.get("max_value", 10)
                            q_text += f" (rate {min_val}-{max_val})"
                        
                        show_progress = survey_config.get("show_progress", True)
                        if show_progress:
                            q_text += f" (1/{len(questions)} questions)"
                        
                        return {
                            "success": True,
                            "message": "Survey started.",
                            "first_question": {
                                "id": start_question_id,
                                "type": q_type,
                                "text": q_text,
                                "options": first_question.get("options") if q_type == "multiple_choice" else None,
                                "min_value": first_question.get("min_value") if q_type == "rating" else None,
                                "max_value": first_question.get("max_value") if q_type == "rating" else None
                            },
                            "total_questions": len(questions)
                        }
                    
                    elif action == "abort":
                        # Abort ongoing survey
                        survey_response = db.query(SurveyResponse).filter(
                            SurveyResponse.call_id == call_id,
                            SurveyResponse.agent_id == agent_id,
                            SurveyResponse.status == SurveyStatus.IN_PROGRESS
                        ).first()
                        
                        if survey_response:
                            survey_response.status = SurveyStatus.ABANDONED
                            survey_response.completed_at = dt.utcnow()
                            db.commit()
                        
                        abort_message = survey_config.get("abort_message", "Anket iptal edildi.")
                        
                        return {
                            "success": True,
                            "message": abort_message,
                            "reason": reason
                        }
                    
                    else:
                        return {
                            "success": False,
                            "message": f"Unknown action: {action}"
                        }
                        
            except Exception as e:
                logger.error(f"Survey control error: {e}")
                return {
                    "success": False,
                    "message": "Survey operation failed"
                }
        
        return {"error": f"Unknown tool: {name}"}
    
    async def _fetch_web_content(self, url: str, query: str) -> str:
        """
        Fetch and extract relevant content from a web page.
        
        Args:
            url: The web page URL to fetch
            query: The search query to find relevant content
            
        Returns:
            Relevant text content from the page
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"Web fetch failed: {url} returned {response.status}")
                        return ""
                    
                    html = await response.text()
                    
            # Parse HTML and extract text
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            # Get text content
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            # If query is provided, try to find relevant sections
            if query:
                query_words = query.lower().split()
                paragraphs = text.split('\n\n')
                relevant = []
                
                for para in paragraphs:
                    para_lower = para.lower()
                    score = sum(1 for word in query_words if word in para_lower)
                    if score > 0:
                        relevant.append((score, para))
                
                # Sort by relevance and take top sections
                relevant.sort(key=lambda x: x[0], reverse=True)
                if relevant:
                    text = '\n\n'.join([p[1] for p in relevant[:5]])
            
            return text[:3000]  # Limit total content
            
        except asyncio.TimeoutError:
            logger.warning(f"Web fetch timeout: {url}")
            return ""
        except Exception as e:
            logger.error(f"Web fetch error: {url} - {e}")
            return ""
    
    async def _delayed_hangup(self, channel_id: str, delay: float):
        """Hangup call after delay"""
        await asyncio.sleep(delay)
        try:
            if self.asterisk:
                await self.asterisk.hangup_channel(channel_id)
        except:
            pass
    
    def _handle_openai_error(self, channel_id: str, error: str):
        """Handle OpenAI error"""
        logger.error(f"OpenAI error [{channel_id}]: {error}")
        
        session = self.sessions.get(channel_id)
        if session:
            session.outcome = "error"
            session.summary = f"AI Error: {error}"
    
    async def hangup_call(self, channel_id: str):
        """Hangup a call"""
        if self.asterisk:
            await self.asterisk.hangup_channel(channel_id)
    
    async def stop(self):
        """Stop the audio bridge"""
        # Disconnect all OpenAI clients
        for client in self.openai_clients.values():
            await client.disconnect()
        self.openai_clients.clear()
        
        # Disconnect Asterisk
        if self.asterisk:
            await self.asterisk.disconnect()
        
        logger.info("AudioBridge stopped")
