"""
Outbound Calls API
Handles outbound call initiation via Asterisk
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
import logging
import asyncio
import aiohttp
import os
import json
import uuid as uuid_lib
import redis

from datetime import datetime
from app.core.database import get_db
from app.models.models import Agent, CallLog, CallStatus

# Redis client for passing agent settings to asterisk bridge
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["Calls"])


def build_conversation_history(db: Session, phone_number: str, agent_id: Optional[int] = None, max_calls: int = 3) -> str:
    """
    Build conversation history context from previous calls to the same number.
    Returns a formatted string for prompt injection.
    """
    try:
        # Normalize phone for matching (last 10 digits)
        normalized = "".join(c for c in phone_number if c.isdigit())
        if len(normalized) > 10:
            normalized = normalized[-10:]
        
        # Query previous calls to this number
        query = db.query(CallLog).filter(
            CallLog.to_number.like(f"%{normalized}")
        ).order_by(CallLog.created_at.desc()).limit(max_calls)
        
        if agent_id:
            query = query.filter(CallLog.agent_id == agent_id)
        
        previous_calls = query.all()
        
        if not previous_calls:
            return ""
        
        history_parts = []
        for i, call in enumerate(previous_calls, 1):
            call_info = [f"### Call #{i} — {call.created_at.strftime('%d.%m.%Y %H:%M') if call.created_at else 'Unknown date'}"]
            
            if call.duration:
                call_info.append(f"- Duration: {call.duration}s")
            if call.outcome:
                call_info.append(f"- Outcome: {call.outcome.value if hasattr(call.outcome, 'value') else call.outcome}")
            if call.sentiment:
                call_info.append(f"- Customer sentiment: {call.sentiment}")
            if call.summary:
                call_info.append(f"- Summary: {call.summary}")
            if call.customer_name:
                call_info.append(f"- Customer name: {call.customer_name}")
            if call.callback_scheduled:
                call_info.append(f"- Callback scheduled: {call.callback_scheduled.strftime('%d.%m.%Y %H:%M')}")
            if call.tags:
                call_info.append(f"- Tags: {', '.join(call.tags)}")
            if call.notes:
                call_info.append(f"- Notes: {call.notes}")
            
            history_parts.append("\n".join(call_info))
        
        return "\n\n".join(history_parts)
    except Exception as e:
        logger.warning(f"Error building conversation history: {e}")
        return ""


# Asterisk ARI Configuration - from environment variables
ARI_HOST = os.environ.get("ASTERISK_HOST", "asterisk")
ARI_PORT = int(os.environ.get("ASTERISK_ARI_PORT", "8088"))
ARI_USERNAME = os.environ.get("ASTERISK_ARI_USER", "voiceai")
ARI_PASSWORD = os.environ.get("ASTERISK_ARI_PASSWORD", "voiceai_ari_secret")
ARI_APP = "voiceai"


class OutboundCallRequest(BaseModel):
    """Request model for initiating an outbound call"""
    phone_number: str = Field(..., description="Phone number to call (without +, e.g., 491234567890)")
    agent_id: Optional[str] = Field(None, description="Agent ID to handle the call")
    caller_id: str = Field(default="491754571258", description="Caller ID to display")
    customer_name: Optional[str] = Field(None, description="Customer name to personalize the call")
    customer_title: Optional[str] = Field(None, description="Customer title: Mr or Mrs")
    variables: Optional[dict] = Field(default=None, description="Custom variables for the call")


class OutboundCallResponse(BaseModel):
    """Response model for outbound call"""
    success: bool
    channel_id: Optional[str] = None
    call_id: Optional[str] = None  # AudioSocket UUID - used for SSE events and transcript
    message: str


class CallStatusResponse(BaseModel):
    """Response model for call status"""
    channel_id: str
    status: str
    caller_id: Optional[str] = None
    connected_number: Optional[str] = None


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number - remove + and any spaces
    Always output without + prefix
    """
    # Remove spaces, dashes, parentheses
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Remove + if present
    if phone.startswith("+"):
        phone = phone[1:]
    
    # Remove leading 00 if present (international format)
    if phone.startswith("00"):
        phone = phone[2:]
    
    return phone


@router.post("/outbound", response_model=OutboundCallResponse)
async def initiate_outbound_call(request: OutboundCallRequest, db: Session = Depends(get_db)):
    """
    Initiate an outbound call via Asterisk
    
    The phone number should be provided WITHOUT the + prefix.
    Example: 491754571258 (not +491754571258)
    
    If agent_id is provided, the agent's settings (voice, model, prompt, language)
    will be applied to the call.
    """
    # Normalize phone number (remove + if accidentally included)
    phone_number = normalize_phone_number(request.phone_number)
    caller_id = normalize_phone_number(request.caller_id)
    
    logger.info(f"Initiating outbound call to {phone_number} with CallerID {caller_id}")
    
    # Generate a UUID for this call - used as AudioSocket UUID
    call_uuid = str(uuid_lib.uuid4())
    
    # Initialize channel variables
    channel_variables = {
        "VOICEAI_UUID": call_uuid,  # Pass UUID to dialplan for AudioSocket
    }
    
    # If agent_id provided, fetch agent settings and store in Redis
    if request.agent_id:
        try:
            agent = db.query(Agent).filter(Agent.id == int(request.agent_id)).first()
            if not agent:
                logger.warning(f"Agent ID {request.agent_id} not found, using defaults")
            else:
                # Model type to string - use new model names
                model_str = str(agent.model_type) if agent.model_type else "gpt-realtime-mini"
                if "RealtimeModel." in model_str:
                    model_str = model_str.replace("RealtimeModel.GPT_REALTIME_MINI", "gpt-realtime-mini").replace("RealtimeModel.GPT_REALTIME", "gpt-realtime")
                
                # Build full prompt from all prompt sections (ElevenLabs Enterprise Prompting Guide structure)
                prompt_parts = []
                # 1. Personality - who the agent is, character traits
                if agent.prompt_role:
                    prompt_parts.append(f"# Personality\n{agent.prompt_role}")
                # 2. Environment - context of the conversation
                if agent.prompt_personality:
                    prompt_parts.append(f"# Environment\n{agent.prompt_personality}")
                # 3. Tone - how to speak (concise, professional, etc.)
                if agent.prompt_context:
                    prompt_parts.append(f"# Tone\n{agent.prompt_context}")
                # 4. Goal - what to accomplish, numbered workflow steps
                if agent.prompt_pronunciations:
                    prompt_parts.append(f"# Goal\n{agent.prompt_pronunciations}")
                # 5. Guardrails - non-negotiable rules (models pay extra attention to this heading)
                if agent.prompt_sample_phrases:
                    prompt_parts.append(f"# Guardrails\n{agent.prompt_sample_phrases}")
                # 6. Tools - tool descriptions with when/how/error handling
                if agent.prompt_tools:
                    prompt_parts.append(f"# Tools\n{agent.prompt_tools}")
                # 7. Character normalization - spoken vs written format rules
                if agent.prompt_rules:
                    prompt_parts.append(f"# Character normalization\n{agent.prompt_rules}")
                # 8. Error handling - tool failure recovery
                if agent.prompt_flow:
                    prompt_parts.append(f"# Error handling\n{agent.prompt_flow}")
                # 9. Legacy: Safety (merged into guardrails for new agents)
                if agent.prompt_safety:
                    prompt_parts.append(f"# Guardrails\n{agent.prompt_safety}")
                # Legacy: Language constraints
                if agent.prompt_language:
                    prompt_parts.append(f"# Language\n{agent.prompt_language}")
                # Knowledge Base - Static information for the agent
                if agent.knowledge_base:
                    prompt_parts.append(f"# Knowledge Base\n{agent.knowledge_base}")
                full_prompt = "\n\n".join(prompt_parts) if prompt_parts else ""
                
                # Store agent settings in Redis keyed by UUID
                VALID_VOICES = {'alloy', 'ash', 'ballad', 'coral', 'echo', 'sage', 'shimmer', 'verse', 'marin', 'cedar'}
                agent_voice = agent.voice if agent.voice in VALID_VOICES else "ash"
                
                # ALL agent settings are passed to asterisk-bridge
                call_setup_data = {
                    # Basic info
                    "agent_id": str(agent.id),
                    "agent_name": agent.name or "AI Agent",
                    "voice": agent_voice,
                    "model": model_str,
                    "language": agent.language or "tr",
                    "prompt": full_prompt,
                    "customer_name": request.customer_name or "",
                    "customer_title": request.customer_title or "",
                    
                    # Greeting settings
                    "greeting_message": agent.greeting_message or "",
                    "first_speaker": agent.first_speaker or "agent",
                    "greeting_uninterruptible": agent.greeting_uninterruptible or False,
                    "first_message_delay": agent.first_message_delay or 0.0,
                    
                    # Call settings
                    "max_duration": agent.max_duration or 300,
                    "silence_timeout": agent.silence_timeout or 10,
                    
                    # Advanced settings - VAD / Turn Detection
                    "temperature": agent.temperature or 0.7,
                    "vad_threshold": agent.vad_threshold or 0.5,
                    "turn_detection": agent.turn_detection or "semantic_vad",
                    "vad_eagerness": agent.vad_eagerness or "low",
                    "silence_duration_ms": agent.silence_duration_ms or 1000,
                    "prefix_padding_ms": agent.prefix_padding_ms or 400,
                    "interrupt_response": agent.interrupt_response if agent.interrupt_response is not None else True,
                    "create_response": agent.create_response if agent.create_response is not None else True,
                    
                    # Advanced settings - Audio
                    "noise_reduction": agent.noise_reduction if agent.noise_reduction is not None else True,
                    "max_output_tokens": agent.max_output_tokens or 500,
                    "speech_speed": agent.speech_speed or 1.0,
                    "idle_timeout_ms": agent.idle_timeout_ms,  # None = no timeout
                    "transcript_model": getattr(agent, 'transcript_model', None) or "gpt-4o-transcribe",
                    
                    # Inactivity messages (JSON)
                    "inactivity_messages": agent.inactivity_messages or [],
                    
                    # Behavior settings
                    "interruptible": agent.interruptible if agent.interruptible is not None else True,
                    "record_calls": agent.record_calls if agent.record_calls is not None else True,
                    "human_transfer": agent.human_transfer if agent.human_transfer is not None else True,
                    
                    # Conversation memory - previous call history for this phone number
                    "conversation_history": build_conversation_history(db, phone_number, agent.id),
                }
                
                if redis_client:
                    try:
                        redis_client.setex(
                            f"call_setup:{call_uuid}",
                            300,  # 5 minutes TTL
                            json.dumps(call_setup_data)
                        )
                        logger.info(f"Call setup stored in Redis: {call_uuid[:8]} -> agent '{agent.name}'")
                    except Exception as redis_err:
                        logger.error(f"Redis store error: {redis_err}")
                
                # Also set channel variables as fallback
                channel_variables["VOICEAI_AGENT_ID"] = str(agent.id)
                channel_variables["VOICEAI_AGENT_NAME"] = agent.name or "AI Agent"
                
                logger.info(f"Using agent '{agent.name}' settings: voice={agent.voice}, model={model_str}, language={agent.language}")
        except Exception as e:
            logger.error(f"Error fetching agent settings: {e}")
    
    # Add customer_name and customer_title if provided
    if request.customer_name:
        channel_variables["VOICEAI_CUSTOMER_NAME"] = request.customer_name
        logger.info(f"Customer name set: {request.customer_name}")
    if request.customer_title:
        channel_variables["VOICEAI_CUSTOMER_TITLE"] = request.customer_title
        logger.info(f"Customer title set: {request.customer_title}")
    
    # Add custom variables if provided
    if request.variables:
        channel_variables.update(request.variables)
    
    try:
        # Build ARI endpoint URL
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels"
        
        # Build request data - use extension/context for dialplan routing
        data = {
            "endpoint": f"PJSIP/{phone_number}@trunk",
            "extension": "s",
            "context": "ai-outbound",
            "callerId": f'"VoiceAI" <{caller_id}>',
            "timeout": 60,
        }
        
        # Add all channel variables
        if channel_variables:
            data["variables"] = channel_variables
        
        # Make ARI request
        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
        
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.post(ari_url, json=data) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    logger.error(f"ARI error: {response.status} - {error_text}")
                    return OutboundCallResponse(
                        success=False,
                        message=f"Failed to initiate call: {error_text}"
                    )
                
                result = await response.json()
                channel_id = result.get("id")

                logger.info(f"Call initiated successfully: {channel_id}")

                # Create CallLog record for this call
                try:
                    agent_id_int = int(request.agent_id) if request.agent_id else None
                    call_log = CallLog(
                        call_sid=call_uuid,
                        status=CallStatus.RINGING,
                        to_number=phone_number,
                        from_number=caller_id,
                        customer_name=request.customer_name or None,
                        agent_id=agent_id_int,
                        started_at=datetime.utcnow(),
                    )
                    db.add(call_log)
                    db.commit()
                    logger.info(f"CallLog created: call_sid={call_uuid}, agent_id={agent_id_int}")
                except Exception as e:
                    logger.warning(f"Failed to create CallLog: {e}")
                    db.rollback()

                return OutboundCallResponse(
                    success=True,
                    channel_id=channel_id,
                    call_id=call_uuid,
                    message=f"Call initiated to {phone_number}"
                )
    
    except aiohttp.ClientError as e:
        logger.error(f"Connection error: {e}")
        return OutboundCallResponse(
            success=False,
            message=f"Connection error: Unable to reach Asterisk ARI. Is Asterisk running?"
        )
    except Exception as e:
        logger.error(f"Error initiating call: {e}")
        return OutboundCallResponse(
            success=False,
            message=f"Error: {str(e)}"
        )


@router.delete("/hangup/{channel_id}")
async def hangup_call(channel_id: str, call_id: Optional[str] = None):
    """
    Hangup an active call by channel ID.
    Also sends hangup signal via Redis for the bridge to stop.
    """
    results = []

    # 0. Send Redis hangup signal to bridge (if call_id/UUID provided)
    if call_id and redis_client:
        try:
            redis_client.setex(f"hangup_signal:{call_id}", 60, "1")
            results.append(f"Redis hangup signal sent for {call_id[:8]}")
            logger.info(f"Redis hangup signal set: hangup_signal:{call_id[:8]}")
        except Exception as e:
            logger.warning(f"Redis hangup signal error: {e}")

    # Skip ARI if channel_id is a placeholder
    if channel_id == "_none":
        return {"success": True, "message": "; ".join(results) if results else "Hangup signal sent via Redis"}

    # 1. Try ARI channel hangup
    try:
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels/{channel_id}"
        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
        
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.delete(ari_url, params={"reason_code": "normal"}) as response:
                if response.status < 400:
                    results.append(f"ARI channel {channel_id} terminated")
                    logger.info(f"ARI hangup successful: {channel_id}")
                elif response.status == 404:
                    results.append(f"ARI channel {channel_id} not found (may have already ended)")
                    logger.info(f"ARI channel already gone: {channel_id}")
                else:
                    error_text = await response.text()
                    results.append(f"ARI error: {error_text}")
    except Exception as e:
        logger.error(f"ARI hangup error: {e}")
        results.append(f"ARI error: {str(e)}")
    
    # 2. Also try to hangup ALL active Asterisk channels (fallback)
    try:
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels"
        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
        
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(ari_url) as response:
                if response.status < 400:
                    channels = await response.json()
                    for ch in channels:
                        ch_id = ch.get("id", "")
                        if ch_id and ch_id != channel_id:
                            try:
                                async with session.delete(
                                    f"http://{ARI_HOST}:{ARI_PORT}/ari/channels/{ch_id}",
                                    params={"reason_code": "normal"}
                                ) as del_resp:
                                    if del_resp.status < 400:
                                        results.append(f"Also terminated related channel: {ch_id}")
                                        logger.info(f"Related channel hangup: {ch_id}")
                            except Exception:
                                pass
    except Exception as e:
        logger.warning(f"Error listing channels for cleanup: {e}")
    
    return {"success": True, "message": "; ".join(results) if results else "Hangup signal sent"}


@router.get("/active")
async def list_active_calls():
    """
    List all active calls/channels
    """
    try:
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels"
        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
        
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(ari_url) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    return {"error": error_text, "channels": []}
                
                channels = await response.json()
                return {"channels": channels, "count": len(channels)}
    
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        return {"error": str(e), "channels": []}


@router.get("/status/{channel_id}")
async def get_call_status(channel_id: str):
    """
    Get status of a specific call
    """
    try:
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels/{channel_id}"
        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
        
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(ari_url) as response:
                if response.status == 404:
                    return {"error": "Channel not found", "status": "ended"}
                elif response.status >= 400:
                    error_text = await response.text()
                    return {"error": error_text}
                
                channel = await response.json()
                return {
                    "channel_id": channel.get("id"),
                    "status": channel.get("state"),
                    "caller_id": channel.get("caller", {}).get("number"),
                    "connected": channel.get("connected", {}).get("number"),
                    "created": channel.get("creationtime"),
                }
    
    except Exception as e:
        logger.error(f"Error getting call status: {e}")
        return {"error": str(e)}


@router.post("/test-call")
async def test_outbound_call(phone_number: str = "491754571258"):
    """
    Quick test endpoint for outbound calls
    Uses default caller ID
    """
    request = OutboundCallRequest(
        phone_number=normalize_phone_number(phone_number),
        caller_id="491754571258"
    )
    return await initiate_outbound_call(request)
