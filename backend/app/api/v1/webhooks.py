import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import json
from datetime import datetime

import redis as redis_lib

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.models import WebhookEndpoint, User, CallLog
from app.models.models import CallStatus, CallOutcome
from app.schemas import WebhookCreate, WebhookResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Redis client for call status updates
try:
    _redis_client = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    _redis_client = None


async def verify_incoming_webhook_signature(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
) -> None:
    """
    Verify HMAC-SHA256 signature on incoming webhooks (Ultravox, AMD).
    Skipped if WEBHOOK_SECRET is not configured.
    """
    secret = settings.WEBHOOK_SECRET
    if not secret:
        return  # No secret configured, skip verification

    if not x_webhook_signature:
        raise HTTPException(status_code=403, detail="Missing webhook signature")

    body = await request.body()
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, x_webhook_signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

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
            "error": "Webhook test failed"
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
    uuid: Optional[str] = None  # For OpenAI provider calls (call_sid)
    phone: Optional[str] = None  # For Ultravox calls (phone number lookup)
    status: str  # MACHINE, HUMAN, NOTSURE
    cause: str = ""  # AMD decision reason
    source: str = ""  # "ultravox" when from Ultravox AMD via Asterisk


@router.post("/amd-result")
async def amd_result_webhook(
    payload: AMDResultRequest,
    db: Session = Depends(get_db),
    _sig: None = Depends(verify_incoming_webhook_signature),
):
    """
    Receive AMD (Answering Machine Detection) result from Asterisk dialplan.

    When Asterisk detects an answering machine on an outbound call,
    it notifies us here so we can update the CallLog and skip the call.
    """
    logger.info(
        f"AMD result received: uuid={payload.uuid}, phone={payload.phone}, "
        f"status={payload.status}, cause={payload.cause}, source={payload.source}"
    )

    call_log = None

    # OpenAI provider: lookup by call_sid (UUID)
    if payload.uuid:
        call_log = db.query(CallLog).filter(CallLog.call_sid == payload.uuid).first()

    # Ultravox provider: lookup by phone number (most recent active call)
    if not call_log and payload.phone:
        phone = payload.phone
        active_statuses = [
            CallStatus.QUEUED, CallStatus.RINGING,
            CallStatus.CONNECTED, CallStatus.TALKING,
        ]
        call_log = (
            db.query(CallLog)
            .filter(
                CallLog.phone_number == phone,
                CallLog.provider == "ultravox",
                CallLog.status.in_(active_statuses),
            )
            .order_by(CallLog.created_at.desc())
            .first()
        )
        # Also try without + prefix
        if not call_log and phone.startswith("+"):
            call_log = (
                db.query(CallLog)
                .filter(
                    CallLog.phone_number == phone[1:],
                    CallLog.provider == "ultravox",
                    CallLog.status.in_(active_statuses),
                )
                .order_by(CallLog.created_at.desc())
                .first()
            )

    if not call_log:
        logger.warning(f"AMD: CallLog not found for uuid={payload.uuid}, phone={payload.phone}")
        return {"status": "not_found"}

    call_log.amd_status = payload.status
    call_log.amd_cause = payload.cause

    if payload.status in ("MACHINE", "NOTSURE"):
        call_log.status = CallStatus.COMPLETED
        call_log.outcome = CallOutcome.VOICEMAIL
        call_log.hangup_cause = f"AMD:{payload.cause}"
        call_log.ended_at = datetime.utcnow()
        call_id_display = (
            payload.uuid[:8] if payload.uuid
            else payload.phone or "unknown"
        )
        logger.info(f"AMD: Marked call {call_id_display} as {payload.status} — will not connect AI agent")

    db.commit()

    return {"status": "ok", "amd_status": payload.status}


# =============================================================================
# CALL FAILED WEBHOOK RECEIVER
# Called by Asterisk dialplan or channel monitor when outbound call fails
# =============================================================================

class CallFailedRequest(PydanticBaseModel):
    uuid: str
    status: str = "BUSY"  # BUSY, NOANSWER, CONGESTION, CHANUNAVAIL
    cause: str = ""  # Asterisk HANGUPCAUSE


DIALSTATUS_TO_SIP = {
    "BUSY": (486, "User Busy"),
    "NOANSWER": (480, "No Answer"),
    "CONGESTION": (503, "Network Congestion"),
    "CHANUNAVAIL": (503, "Channel Unavailable"),
    "CANCEL": (487, "Request Terminated"),
}


@router.post("/call-failed")
async def call_failed_webhook(
    payload: CallFailedRequest,
    db: Session = Depends(get_db),
    _sig: None = Depends(verify_incoming_webhook_signature),
):
    """
    Receive call-failed notification from Asterisk dialplan.

    When an outbound call fails (busy, no-answer, congestion) before
    the AudioSocket bridge starts, Asterisk notifies us here.
    """
    sip_code, hangup_cause = DIALSTATUS_TO_SIP.get(
        payload.status, (480, payload.status)
    )
    logger.info(
        f"Call failed: uuid={payload.uuid[:8]}, status={payload.status}, "
        f"sip_code={sip_code}, cause={payload.cause}"
    )

    call_log = db.query(CallLog).filter(CallLog.call_sid == payload.uuid).first()
    if not call_log:
        logger.warning(f"Call failed: CallLog not found for uuid={payload.uuid[:8]}")
        return {"status": "not_found"}

    # Only update if not already completed/failed
    if call_log.status in (CallStatus.RINGING, CallStatus.QUEUED, CallStatus.CONNECTED):
        call_log.status = CallStatus.NO_ANSWER
        call_log.outcome = CallOutcome.NO_ANSWER
        call_log.sip_code = sip_code
        call_log.hangup_cause = hangup_cause
        call_log.ended_at = datetime.utcnow()
        db.commit()
        logger.info(f"Call failed: Marked call {payload.uuid[:8]} as {call_log.status}")
    else:
        logger.info(f"Call failed: Call {payload.uuid[:8]} already in state {call_log.status}, skipping")

    return {"status": "ok", "sip_code": sip_code}


# =============================================================================
# ULTRAVOX WEBHOOK RECEIVER
# =============================================================================

import math
ULTRAVOX_RATE_PER_MINUTE = 0.05
ULTRAVOX_DECIMINUTE_RATE = 0.005  # $0.005 per 6-second increment

# Ultravox TerminationReasonEnum → SIP code mapping
ULTRAVOX_TERMINATION_TO_SIP = {
    "SIP_TERMINATION_NORMAL": (200, "Normal Clearing"),
    "SIP_TERMINATION_INVALID_NUMBER": (404, "Number Not Found"),
    "SIP_TERMINATION_TIMEOUT": (480, "No Answer (Timeout)"),
    "SIP_TERMINATION_DESTINATION_UNAVAILABLE": (503, "Destination Unavailable"),
    "SIP_TERMINATION_BUSY": (486, "User Busy"),
    "SIP_TERMINATION_CANCELED": (487, "Call Canceled"),
    "SIP_TERMINATION_REJECTED": (603, "Call Rejected"),
    "SIP_TERMINATION_UNKNOWN": (0, "Unknown"),
}

# Ultravox endReason → (CallStatus, CallOutcome) mapping
ULTRAVOX_END_REASON_MAP = {
    "hangup": (CallStatus.COMPLETED, CallOutcome.SUCCESS),
    "agent_hangup": (CallStatus.COMPLETED, CallOutcome.SUCCESS),
    "timeout": (CallStatus.COMPLETED, CallOutcome.NO_ANSWER),
    "unjoined": (CallStatus.FAILED, CallOutcome.NO_ANSWER),
    "connection_error": (CallStatus.FAILED, CallOutcome.FAILED),
    "system_error": (CallStatus.FAILED, CallOutcome.FAILED),
}


@router.post("/ultravox")
async def ultravox_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _sig: None = Depends(verify_incoming_webhook_signature),
):
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
        call_log.ended_at = datetime.utcnow()

        # Duration
        duration = call_data.get("duration") or call_data.get("durationSeconds")
        if duration:
            call_log.duration = int(duration)
        elif call_log.connected_at:
            call_log.duration = int((call_log.ended_at - call_log.connected_at).total_seconds())

        # ---- Fetch full call details from Ultravox API for SIP info ----
        sip_termination_reason = None
        full_call_data = None
        try:
            from app.services.ultravox_service import UltravoxService
            service = UltravoxService()
            full_call_data = await service.get_call(ultravox_call_id)

            # Extract sipDetails
            sip_details = full_call_data.get("sipDetails", {}) or {}
            sip_termination_reason = sip_details.get("terminationReason")

            # Also pick up endReason from the full call data if webhook didn't provide it
            if not call_data.get("endReason") and full_call_data.get("endReason"):
                call_data["endReason"] = full_call_data["endReason"]

            logger.info(
                f"[Ultravox webhook] SIP details: "
                f"termination={sip_termination_reason}, "
                f"endReason={call_data.get('endReason')}"
            )
        except Exception as e:
            logger.warning(f"[Ultravox webhook] Failed to fetch call details: {e}")

        # ---- Map SIP termination reason to sip_code + hangup_cause ----
        if sip_termination_reason and sip_termination_reason in ULTRAVOX_TERMINATION_TO_SIP:
            sip_code, hangup_cause = ULTRAVOX_TERMINATION_TO_SIP[sip_termination_reason]
            call_log.sip_code = sip_code
            call_log.hangup_cause = hangup_cause
        elif sip_termination_reason:
            # Unknown termination reason — store raw value
            call_log.hangup_cause = sip_termination_reason

        # ---- End reason → status + outcome mapping ----
        end_reason = call_data.get("endReason", "")

        # First: use endReason for basic mapping
        if end_reason in ULTRAVOX_END_REASON_MAP:
            status, outcome = ULTRAVOX_END_REASON_MAP[end_reason]
            call_log.status = status
            call_log.outcome = outcome
        else:
            call_log.status = CallStatus.COMPLETED
            call_log.outcome = CallOutcome.SUCCESS

        # Second: override outcome based on SIP termination reason (more precise)
        if sip_termination_reason:
            if sip_termination_reason == "SIP_TERMINATION_INVALID_NUMBER":
                call_log.status = CallStatus.FAILED
                call_log.outcome = CallOutcome.FAILED
            elif sip_termination_reason == "SIP_TERMINATION_BUSY":
                call_log.status = CallStatus.BUSY
                call_log.outcome = CallOutcome.BUSY
            elif sip_termination_reason == "SIP_TERMINATION_TIMEOUT":
                call_log.status = CallStatus.NO_ANSWER
                call_log.outcome = CallOutcome.NO_ANSWER
            elif sip_termination_reason == "SIP_TERMINATION_DESTINATION_UNAVAILABLE":
                call_log.status = CallStatus.FAILED
                call_log.outcome = CallOutcome.FAILED
            elif sip_termination_reason == "SIP_TERMINATION_REJECTED":
                call_log.status = CallStatus.FAILED
                call_log.outcome = CallOutcome.BUSY
            elif sip_termination_reason == "SIP_TERMINATION_CANCELED":
                call_log.status = CallStatus.FAILED
                call_log.outcome = CallOutcome.FAILED

        # AMD override: if Asterisk AMD already detected voicemail, preserve that outcome
        # AMD webhook fires before Ultravox webhook, so amd_status is already set
        if call_log.amd_status in ("MACHINE", "NOTSURE"):
            call_log.status = CallStatus.COMPLETED
            call_log.outcome = CallOutcome.VOICEMAIL
            logger.info(
                f"[Ultravox webhook] AMD override: {call_log.amd_status}, "
                f"preserving outcome=VOICEMAIL"
            )

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
            if not full_call_data:
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

        # Set Redis call status for frontend polling detection
        if _redis_client and call_log.call_sid:
            try:
                status_val = call_log.status.value if call_log.status else "completed"
                # Map to frontend-friendly status names
                redis_status_map = {
                    "failed": "failed",
                    "no_answer": "no-answer",
                    "busy": "busy",
                    "completed": "completed",
                }
                redis_status = redis_status_map.get(status_val, status_val)
                _redis_client.setex(
                    f"call_status:{call_log.call_sid}",
                    300,  # 5 min TTL
                    redis_status,
                )
                logger.info(
                    f"[Ultravox webhook] Redis call_status:{call_log.call_sid[:8]} = {redis_status}"
                )
            except Exception as redis_err:
                logger.warning(f"Redis status update failed (non-fatal): {redis_err}")

        db.commit()

        # Broadcast to frontend via WebSocket
        try:
            from app.api.v1.calls import connection_manager
            await connection_manager.broadcast({
                "type": "call_ended",
                "call_id": call_log.id,
                "call_sid": call_log.call_sid,
                "status": call_log.status.value if call_log.status else "completed",
                "outcome": call_log.outcome.value if call_log.outcome else None,
                "sip_code": call_log.sip_code,
                "hangup_cause": call_log.hangup_cause,
                "duration": call_log.duration,
                "provider": "ultravox",
            })
        except Exception:
            pass

        return {"status": "ok"}

    return {"status": "ignored", "reason": f"unhandled event: {event_type}"}
