"""
Audio Bridge - Connects Asterisk audio stream with OpenAI Realtime API
Handles bidirectional audio streaming and transcoding
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime

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
        # Build configuration
        config = RealtimeConfig(
            voice=session.agent_config.get("voice", "alloy"),
            language=session.agent_config.get("language", "tr"),
            temperature=session.agent_config.get("temperature", 0.7),
            turn_detection_threshold=session.agent_config.get("vad_threshold", 0.5)
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
            return {"success": True, "message": "Ödeme sözü kaydedildi"}
        
        elif name == "transfer_to_human":
            reason = args.get("reason", "Müşteri talebi")
            
            # Transfer the call
            # await self.asterisk.transfer_call(channel_id, "PJSIP/operator")
            
            session.outcome = "transferred"
            return {"success": True, "message": f"Aktarılıyor: {reason}"}
        
        elif name == "schedule_callback":
            session.callback_scheduled = args.get("datetime")
            return {"success": True, "message": "Geri arama planlandı"}
        
        elif name == "end_call":
            session.outcome = args.get("outcome", "completed")
            session.summary = args.get("summary", "")
            
            # End the call after a short delay
            asyncio.create_task(self._delayed_hangup(channel_id, 2))
            
            return {"success": True, "message": "Görüşme sonlandırılıyor"}
        
        return {"error": f"Unknown tool: {name}"}
    
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
