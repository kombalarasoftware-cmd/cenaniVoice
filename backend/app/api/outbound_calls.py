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

from app.core.database import get_db
from app.models.models import Agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["Calls"])


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
    variables: Optional[dict] = Field(default=None, description="Custom variables for the call")


class OutboundCallResponse(BaseModel):
    """Response model for outbound call"""
    success: bool
    channel_id: Optional[str] = None
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
    
    # Initialize channel variables
    channel_variables = {}
    
    # If agent_id provided, fetch agent settings from database
    if request.agent_id:
        try:
            agent = db.query(Agent).filter(Agent.id == int(request.agent_id)).first()
            if not agent:
                logger.warning(f"Agent ID {request.agent_id} not found, using defaults")
            else:
                # Set agent configuration as channel variables
                channel_variables["VOICEAI_AGENT_ID"] = str(agent.id)
                channel_variables["VOICEAI_AGENT_NAME"] = agent.name or "AI Agent"
                channel_variables["VOICEAI_VOICE"] = agent.voice or "alloy"
                # Model type'ı string olarak gönder (enum değil)
                model_str = str(agent.model_type) if agent.model_type else "gpt-4o-realtime-preview-2024-12-17"
                if "RealtimeModel." in model_str:
                    model_str = model_str.replace("RealtimeModel.GPT_REALTIME_MINI", "gpt-4o-realtime-preview-2024-12-17").replace("RealtimeModel.GPT_REALTIME", "gpt-4o-realtime-preview-2024-12-17")
                channel_variables["VOICEAI_MODEL"] = model_str
                channel_variables["VOICEAI_LANGUAGE"] = agent.language or "tr"
                channel_variables["VOICEAI_PROMPT"] = agent.prompt_role or ""
                
                logger.info(f"Using agent '{agent.name}' settings: voice={agent.voice}, model={model_str}, language={agent.language}")
        except Exception as e:
            logger.error(f"Error fetching agent settings: {e}")
    
    # Add customer_name if provided
    if request.customer_name:
        channel_variables["VOICEAI_CUSTOMER_NAME"] = request.customer_name
        logger.info(f"Customer name set: {request.customer_name}")
    
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
                
                return OutboundCallResponse(
                    success=True,
                    channel_id=channel_id,
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
async def hangup_call(channel_id: str):
    """
    Hangup an active call by channel ID
    """
    try:
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels/{channel_id}"
        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
        
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.delete(ari_url, params={"reason_code": "normal"}) as response:
                if response.status == 404:
                    return {"success": False, "message": "Channel not found"}
                elif response.status >= 400:
                    error_text = await response.text()
                    return {"success": False, "message": f"Error: {error_text}"}
                
                return {"success": True, "message": f"Call {channel_id} terminated"}
    
    except Exception as e:
        logger.error(f"Error hanging up call: {e}")
        return {"success": False, "message": str(e)}


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
