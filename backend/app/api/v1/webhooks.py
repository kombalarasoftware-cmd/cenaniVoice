from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
import logging
import json
from datetime import datetime

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import WebhookEndpoint, User, CallLog
from app.models.models import CallStatus, CallOutcome
from app.schemas import WebhookCreate, WebhookResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Available webhook events
WEBHOOK_EVENTS = [
    "call.started",
    "call.connected",
    "call.completed",
    "call.failed",
    "call.transferred",
    "campaign.started",
    "campaign.completed",
    "campaign.paused",
    "recording.ready",
    "transcription.ready",
]


@router.get("/events")
async def list_webhook_events():
    """List all available webhook events"""
    return WEBHOOK_EVENTS


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all webhooks"""
    webhooks = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.owner_id == current_user.id
    ).all()
    return webhooks


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new webhook endpoint"""
    import secrets
    
    # Validate events
    invalid_events = [e for e in webhook_data.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid_events}"
        )
    
    webhook = WebhookEndpoint(
        url=webhook_data.url,
        events=webhook_data.events,
        secret=secrets.token_urlsafe(32),
        owner_id=current_user.id
    )
    
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    return webhook


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get webhook details"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a webhook"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Validate events
    invalid_events = [e for e in webhook_data.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid_events}"
        )
    
    webhook.url = webhook_data.url
    webhook.events = webhook_data.events
    
    db.commit()
    db.refresh(webhook)
    
    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a webhook"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()
    
    return {"message": "Webhook deleted"}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a test event to webhook"""
    import httpx
    import hmac
    import hashlib
    import json
    from datetime import datetime
    
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Create test payload
    payload = {
        "event": "test",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "message": "This is a test webhook delivery"
        }
    }
    
    # Create signature
    payload_str = json.dumps(payload)
    secret_key = webhook.secret or ""
    signature = hmac.new(
        secret_key.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": "test"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=10
            )
        
        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "response": response.text[:500]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/{webhook_id}/toggle")
async def toggle_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enable/disable a webhook"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook.is_active = not webhook.is_active
    db.commit()
    
    return {
        "message": f"Webhook {'enabled' if webhook.is_active else 'disabled'}",
        "is_active": webhook.is_active
    }


@router.get("/{webhook_id}/secret")
async def get_webhook_secret(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get webhook signing secret"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"secret": webhook.secret}


@router.post("/{webhook_id}/rotate-secret")
async def rotate_webhook_secret(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rotate webhook signing secret"""
    import secrets
    
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook.secret = secrets.token_urlsafe(32)
    db.commit()
    
    return {
        "message": "Secret rotated",
        "secret": webhook.secret
    }


# =============================================================================
# AMD (Answering Machine Detection) WEBHOOK RECEIVER
# Called by Asterisk dialplan when AMD() detects a machine
# =============================================================================

from pydantic import BaseModel as PydanticBaseModel


class AMDResultRequest(PydanticBaseModel):
    uuid: str
    status: str  # MACHINE, HUMAN, NOTSURE
    cause: str = ""  # AMD decision reason


@router.post("/amd-result")
async def amd_result_webhook(payload: AMDResultRequest, db: Session = Depends(get_db)):
    """
    Receive AMD (Answering Machine Detection) result from Asterisk dialplan.

    When Asterisk detects an answering machine on an outbound call,
    it notifies us here so we can update the CallLog and skip the call.
    """
    logger.info(f"AMD result received: uuid={payload.uuid[:8]}, status={payload.status}, cause={payload.cause}")

    call_log = db.query(CallLog).filter(CallLog.call_sid == payload.uuid).first()
    if not call_log:
        logger.warning(f"AMD: CallLog not found for uuid={payload.uuid[:8]}")
        return {"status": "not_found"}

    call_log.amd_status = payload.status
    call_log.amd_cause = payload.cause

    if payload.status == "MACHINE":
        call_log.status = CallStatus.COMPLETED
        call_log.outcome = CallOutcome.NO_ANSWER  # re-use no_answer for machines
        call_log.hangup_cause = f"AMD:{payload.cause}"
        call_log.ended_at = datetime.utcnow()
        logger.info(f"AMD: Marked call {payload.uuid[:8]} as machine — will not connect AI agent")

    db.commit()

    return {"status": "ok", "amd_status": payload.status}


# =============================================================================
# ULTRAVOX WEBHOOK RECEIVER
# =============================================================================

import math
ULTRAVOX_RATE_PER_MINUTE = 0.05
ULTRAVOX_DECIMINUTE_RATE = 0.005  # $0.005 per 6-second increment


@router.post("/ultravox")
async def ultravox_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive webhook events from Ultravox.

    Events handled:
    - call.started: Call connected
    - call.ended: Call finished — fetch transcript, recording, update CallLog
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = body.get("event", "")
    call_data = body.get("call", body)  # Ultravox may nest under "call"
    ultravox_call_id = call_data.get("callId") or call_data.get("call_id") or body.get("callId")

    logger.info(f"[Ultravox webhook] event={event_type} call_id={ultravox_call_id}")

    if not ultravox_call_id:
        return {"status": "ignored", "reason": "no call ID"}

    # Look up CallLog by ultravox_call_id
    call_log = db.query(CallLog).filter(CallLog.ultravox_call_id == ultravox_call_id).first()

    if not call_log:
        logger.warning(f"[Ultravox webhook] CallLog not found for {ultravox_call_id}")
        return {"status": "ignored", "reason": "call not found"}

    # ------- call.started -------
    if event_type == "call.started":
        call_log.status = CallStatus.CONNECTED
        call_log.connected_at = datetime.utcnow()
        db.commit()
        return {"status": "ok"}

    # ------- call.ended -------
    if event_type in ("call.ended", "call.billed"):
        call_log.status = CallStatus.COMPLETED
        call_log.ended_at = datetime.utcnow()

        # Duration
        duration = call_data.get("duration") or call_data.get("durationSeconds")
        if duration:
            call_log.duration = int(duration)
        elif call_log.connected_at:
            call_log.duration = int((call_log.ended_at - call_log.connected_at).total_seconds())

        # End reason -> outcome mapping
        end_reason = call_data.get("endReason", "")
        if end_reason in ("hangup", "completed"):
            call_log.outcome = CallOutcome.SUCCESS
        elif end_reason in ("no_answer", "timeout"):
            call_log.outcome = CallOutcome.NO_ANSWER
        elif end_reason == "busy":
            call_log.outcome = CallOutcome.BUSY
        elif end_reason == "error":
            call_log.outcome = CallOutcome.FAILED
        else:
            call_log.outcome = CallOutcome.SUCCESS

        # Cost: deciminute-based (6-second increments, rounded up)
        if call_log.duration:
            deciminutes = math.ceil(call_log.duration / 6)
            call_log.estimated_cost = round(deciminutes * ULTRAVOX_DECIMINUTE_RATE, 4)

        # Provider & model info
        call_log.model_used = "ultravox"
        if not call_log.provider:
            call_log.provider = "ultravox"

        # Recording URL
        recording_url = call_data.get("recordingUrl") or call_data.get("recording_url")
        if recording_url:
            call_log.recording_url = recording_url

        # Fetch transcript from Ultravox API
        try:
            from app.services.ultravox_service import UltravoxService
            service = UltravoxService()
            messages = await service.get_call_messages(ultravox_call_id)
            if messages:
                transcript_lines = []
                for msg in messages:
                    role = msg.get("role", "unknown")
                    text = msg.get("text", "")
                    if text:
                        transcript_lines.append(f"{role}: {text}")
                call_log.transcription = "\n".join(transcript_lines)
        except Exception as e:
            logger.warning(f"Failed to fetch Ultravox transcript: {e}")

        db.commit()

        # Broadcast to frontend via WebSocket
        try:
            from app.api.v1.calls import connection_manager
            await connection_manager.broadcast({
                "type": "call_ended",
                "call_id": call_log.id,
                "call_sid": call_log.call_sid,
                "status": "completed",
                "duration": call_log.duration,
                "provider": "ultravox",
            })
        except Exception:
            pass

        return {"status": "ok"}

    return {"status": "ignored", "reason": f"unhandled event: {event_type}"}
