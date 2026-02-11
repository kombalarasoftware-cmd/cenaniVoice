"""
Outbound Calls API
Handles outbound call initiation via Asterisk (OpenAI) or Ultravox REST API.
Routes to the appropriate provider based on agent.provider setting.
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
from app.core.config import settings
from app.models.models import Agent, CallLog, CallStatus
from app.models import User
from app.services.provider_factory import get_provider
from app.api.v1.auth import get_current_user

# Redis client for passing agent settings to asterisk bridge
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
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
        )
        
        if agent_id:
            query = query.filter(CallLog.agent_id == agent_id)
        
        query = query.order_by(CallLog.created_at.desc()).limit(max_calls)
        
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


# Asterisk ARI Configuration - from settings (environment variables)
ARI_HOST = settings.ASTERISK_HOST
ARI_PORT = settings.ASTERISK_ARI_PORT
ARI_USERNAME = settings.ASTERISK_ARI_USER
ARI_PASSWORD = settings.ASTERISK_ARI_PASSWORD
ARI_APP = "voiceai"


class OutboundCallRequest(BaseModel):
    """Request model for initiating an outbound call"""
    phone_number: str = Field(..., description="Phone number to call (without +, e.g., 491234567890)")
    agent_id: Optional[str] = Field(None, description="Agent ID to handle the call")
    caller_id: str = Field(default="491632086421", description="Caller ID to display")
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
async def initiate_outbound_call(
    request: OutboundCallRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Initiate an outbound call.

    Routes to the appropriate provider based on agent.provider setting:
    - OpenAI: Asterisk ARI -> AudioSocket -> OpenAI Realtime WebSocket
    - Ultravox: Ultravox REST API -> native SIP (bypasses Asterisk)

    The phone number should be provided WITHOUT the + prefix.
    """
    phone_number = normalize_phone_number(request.phone_number)
    caller_id = normalize_phone_number(request.caller_id)

    logger.info(f"Initiating outbound call to {phone_number} with CallerID {caller_id}")

    # Resolve agent and its provider
    agent = None
    if request.agent_id:
        agent = db.query(Agent).filter(Agent.id == int(request.agent_id)).first()
        if not agent:
            logger.warning(f"Agent ID {request.agent_id} not found, using default OpenAI flow")

    provider_type = getattr(agent, "provider", "openai") if agent else "openai"

    # -----------------------------------------------------------------
    # ULTRAVOX PROVIDER PATH
    # -----------------------------------------------------------------
    if provider_type == "ultravox" and agent:
        try:
            provider = get_provider("ultravox")
            conversation_history = build_conversation_history(db, phone_number, agent.id)

            result = await provider.initiate_call(
                agent=agent,
                phone_number=phone_number,
                caller_id=caller_id,
                customer_name=request.customer_name or "",
                customer_title=request.customer_title or "",
                conversation_history=conversation_history,
                variables=request.variables,
            )

            # Create CallLog
            try:
                call_log = CallLog(
                    call_sid=result["call_id"],
                    provider="ultravox",
                    ultravox_call_id=result.get("ultravox_call_id"),
                    status=CallStatus.RINGING,
                    to_number=phone_number,
                    from_number=caller_id,
                    customer_name=request.customer_name or None,
                    agent_id=agent.id,
                    started_at=datetime.utcnow(),
                )
                db.add(call_log)
                db.commit()
                logger.info(f"CallLog created (ultravox): call_sid={result['call_id']}")
            except Exception as e:
                logger.warning(f"Failed to create CallLog: {e}")
                db.rollback()

            return OutboundCallResponse(
                success=True,
                channel_id=None,
                call_id=result["call_id"],
                message=f"Ultravox call initiated to {phone_number}",
            )
        except Exception as e:
            logger.error(f"Ultravox call error: {e}")
            return OutboundCallResponse(success=False, message="Ultravox call failed. Please try again.")

    # -----------------------------------------------------------------
    # OPENAI PROVIDER PATH (existing Asterisk ARI flow)
    # -----------------------------------------------------------------
    call_uuid = str(uuid_lib.uuid4())
    channel_variables = {"VOICEAI_UUID": call_uuid}

    if agent:
        try:
            model_str = str(agent.model_type) if agent.model_type else "gpt-realtime-mini"
            if "RealtimeModel." in model_str:
                model_str = model_str.replace("RealtimeModel.GPT_REALTIME_MINI", "gpt-realtime-mini").replace("RealtimeModel.GPT_REALTIME", "gpt-realtime")

            # Build full prompt from all prompt sections
            prompt_parts = []
            if agent.prompt_role:
                prompt_parts.append(f"# Personality\n{agent.prompt_role}")
            if agent.prompt_personality:
                prompt_parts.append(f"# Environment\n{agent.prompt_personality}")
            if agent.prompt_context:
                prompt_parts.append(f"# Tone\n{agent.prompt_context}")
            if agent.prompt_pronunciations:
                prompt_parts.append(f"# Goal\n{agent.prompt_pronunciations}")
            if agent.prompt_sample_phrases:
                prompt_parts.append(f"# Guardrails\n{agent.prompt_sample_phrases}")
            if agent.prompt_tools:
                prompt_parts.append(f"# Tools\n{agent.prompt_tools}")
            if agent.prompt_rules:
                prompt_parts.append(f"# Character normalization\n{agent.prompt_rules}")
            if agent.prompt_flow:
                prompt_parts.append(f"# Error handling\n{agent.prompt_flow}")
            if agent.prompt_safety:
                prompt_parts.append(f"# Guardrails\n{agent.prompt_safety}")
            if agent.prompt_language:
                prompt_parts.append(f"# Language\n{agent.prompt_language}")
            if agent.knowledge_base:
                prompt_parts.append(f"# Knowledge Base\n{agent.knowledge_base}")
            full_prompt = "\n\n".join(prompt_parts) if prompt_parts else ""

            VALID_VOICES = {'alloy', 'ash', 'ballad', 'coral', 'echo', 'sage', 'shimmer', 'verse', 'marin', 'cedar'}
            agent_voice = agent.voice if agent.voice in VALID_VOICES else "ash"

            call_setup_data = {
                "agent_id": str(agent.id),
                "agent_name": agent.name or "AI Agent",
                "voice": agent_voice,
                "model": model_str,
                "language": agent.language or "tr",
                "prompt": full_prompt,
                "customer_name": request.customer_name or "",
                "customer_title": request.customer_title or "",
                "greeting_message": agent.greeting_message or "",
                "first_speaker": agent.first_speaker or "agent",
                "greeting_uninterruptible": agent.greeting_uninterruptible or False,
                "first_message_delay": agent.first_message_delay or 0.0,
                "max_duration": agent.max_duration or 300,
                "silence_timeout": agent.silence_timeout or 10,
                "temperature": agent.temperature or 0.7,
                "vad_threshold": agent.vad_threshold or 0.5,
                "turn_detection": agent.turn_detection or "semantic_vad",
                "vad_eagerness": agent.vad_eagerness or "low",
                "silence_duration_ms": agent.silence_duration_ms or 1000,
                "prefix_padding_ms": agent.prefix_padding_ms or 400,
                "interrupt_response": agent.interrupt_response if agent.interrupt_response is not None else True,
                "create_response": agent.create_response if agent.create_response is not None else True,
                "noise_reduction": agent.noise_reduction if agent.noise_reduction is not None else True,
                "max_output_tokens": agent.max_output_tokens or 500,
                "speech_speed": agent.speech_speed or 1.0,
                "idle_timeout_ms": agent.idle_timeout_ms,
                "transcript_model": getattr(agent, 'transcript_model', None) or "gpt-4o-transcribe",
                "inactivity_messages": agent.inactivity_messages or [],
                "interruptible": agent.interruptible if agent.interruptible is not None else True,
                "record_calls": agent.record_calls if agent.record_calls is not None else True,
                "human_transfer": agent.human_transfer if agent.human_transfer is not None else True,
                "conversation_history": build_conversation_history(db, phone_number, agent.id),
            }

            if redis_client:
                try:
                    redis_client.setex(f"call_setup:{call_uuid}", 300, json.dumps(call_setup_data))
                    logger.info(f"Call setup stored in Redis: {call_uuid[:8]} -> agent '{agent.name}'")
                except Exception as redis_err:
                    logger.error(f"Redis store error: {redis_err}")

            channel_variables["VOICEAI_AGENT_ID"] = str(agent.id)
            channel_variables["VOICEAI_AGENT_NAME"] = agent.name or "AI Agent"

            logger.info(f"Using agent '{agent.name}' settings: voice={agent.voice}, model={model_str}, language={agent.language}")
        except Exception as e:
            logger.error(f"Error fetching agent settings: {e}")

    if request.customer_name:
        channel_variables["VOICEAI_CUSTOMER_NAME"] = request.customer_name
    if request.customer_title:
        channel_variables["VOICEAI_CUSTOMER_TITLE"] = request.customer_title
    if request.variables:
        channel_variables.update(request.variables)

    try:
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels"
        data = {
            "endpoint": f"PJSIP/{phone_number}@trunk",
            "extension": "s",
            "context": "ai-outbound",
            "callerId": f'"VoiceAI" <{caller_id}>',
            "timeout": 60,
        }
        if channel_variables:
            data["variables"] = channel_variables

        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)

        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.post(ari_url, json=data) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    logger.error(f"ARI error: {response.status} - {error_text}")
                    return OutboundCallResponse(success=False, message=f"Failed to initiate call: {error_text}")

                result = await response.json()
                channel_id = result.get("id")
                logger.info(f"Call initiated successfully: {channel_id}")

                try:
                    agent_id_int = int(request.agent_id) if request.agent_id else None
                    call_log = CallLog(
                        call_sid=call_uuid,
                        provider="openai",
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
                    message=f"Call initiated to {phone_number}",
                )

    except aiohttp.ClientError as e:
        logger.error(f"Connection error: {e}")
        return OutboundCallResponse(success=False, message="Connection error: Unable to reach Asterisk ARI. Is Asterisk running?")
    except Exception as e:
        logger.error(f"Error initiating call: {e}")
        return OutboundCallResponse(success=False, message="Failed to initiate call. Please try again.")


@router.delete("/hangup/{channel_id}")
async def hangup_call(
    channel_id: str,
    call_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
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

    # Skip ARI if channel_id is a placeholder (e.g. Ultravox calls have no Asterisk channel)
    if channel_id == "_none":
        # Check if this is an Ultravox call and terminate via Ultravox API
        if call_id and redis_client:
            try:
                ultravox_call_id = redis_client.get(f"call_ultravox:{call_id}")
                if ultravox_call_id:
                    from app.services.ultravox_service import UltravoxService
                    svc = UltravoxService()
                    try:
                        await svc.end_call(ultravox_call_id)
                        results.append(f"Ultravox call {ultravox_call_id[:8]} terminated")
                        logger.info(f"Ultravox hangup successful: {ultravox_call_id}")
                    except Exception as uv_err:
                        logger.warning(f"Ultravox end_call failed, trying delete: {uv_err}")
                        try:
                            await svc.delete_call(ultravox_call_id)
                            results.append(f"Ultravox call {ultravox_call_id[:8]} force-deleted")
                            logger.info(f"Ultravox force-delete successful: {ultravox_call_id}")
                        except Exception as del_err:
                            logger.error(f"Ultravox delete also failed: {del_err}")
                            results.append(f"Ultravox hangup failed: {del_err}")
                else:
                    logger.info(f"No Ultravox mapping found for call_id={call_id[:8]}")
            except Exception as e:
                logger.warning(f"Ultravox hangup lookup error: {e}")

        # Also update call status in DB
        if call_id:
            try:
                from app.models.models import CallLog
                call_log = db.query(CallLog).filter(CallLog.call_sid == call_id).first()
                if call_log and call_log.status not in ("completed", "failed", "no-answer"):
                    call_log.status = "completed"
                    db.commit()
                    results.append("Call status updated to completed")
            except Exception as db_err:
                logger.warning(f"DB status update error: {db_err}")

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
    
    return {"success": True, "message": "; ".join(results) if results else "Hangup signal sent"}


@router.get("/active")
async def list_active_calls(
    current_user: User = Depends(get_current_user),
):
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
        return {"error": "Failed to list channels", "channels": []}


@router.get("/status/{channel_id}")
async def get_call_status(
    channel_id: str,
    current_user: User = Depends(get_current_user),
):
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
        return {"error": "Failed to get call status"}



