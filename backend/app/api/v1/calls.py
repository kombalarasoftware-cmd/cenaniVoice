"""
Call management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload, contains_eager
from typing import List, Optional, Dict
from datetime import datetime
import json
import asyncio
import logging
import redis
import os

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from sqlalchemy import or_
from app.models import CallLog, User, Campaign, Agent
from app.models.models import CallStatus, CallOutcome, CallTag
from app.schemas import CallLogResponse
from app.schemas.schemas import CallTagsUpdate, CallTagsResponse

router = APIRouter(prefix="/calls", tags=["Calls"])
logger = logging.getLogger(__name__)

# Redis client for transcript retrieval
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Redis connected for transcript retrieval")
except Exception as e:
    logger.warning(f"Redis not available for transcript: {e}")
    redis_client = None


class ConnectionManager:
    """
    WebSocket connection manager with limits and heartbeat support.
    """

    def __init__(self, max_connections: int = 100):
        self.active_connections: Dict[str, WebSocket] = {}
        self.max_connections = max_connections
        self.heartbeat_interval = settings.WEBSOCKET_HEARTBEAT_INTERVAL

    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        Accept a new WebSocket connection if under limit.
        Returns True if connected, False if limit reached.
        """
        if len(self.active_connections) >= self.max_connections:
            logger.warning(f"WebSocket connection rejected: limit reached ({self.max_connections})")
            await websocket.close(code=1013, reason="Connection limit reached")
            return False

        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id} (total: {len(self.active_connections)})")
        return True

    def disconnect(self, client_id: str) -> None:
        """Remove a connection from the manager."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id} (total: {len(self.active_connections)})")

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        disconnected = []
        message_json = json.dumps(message)

        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

    async def send_personal(self, client_id: str, message: dict) -> bool:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.warning(f"Failed to send to {client_id}: {e}")
                self.disconnect(client_id)
        return False


# Create global connection manager
connection_manager = ConnectionManager(max_connections=settings.MAX_WEBSOCKET_CONNECTIONS)


@router.get("")
async def list_calls(
    status: Optional[CallStatus] = None,
    outcome: Optional[CallOutcome] = None,
    campaign_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = Query(None, description="Search by customer name, phone number or call SID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List call logs with pagination, filtering and search"""
    # Use outerjoin so calls without campaign (console test calls) also appear
    # Use contains_eager (not joinedload) since we do explicit outerjoin
    query = db.query(CallLog).outerjoin(
        Campaign, CallLog.campaign_id == Campaign.id
    ).outerjoin(
        Agent, CallLog.agent_id == Agent.id
    ).options(
        contains_eager(CallLog.campaign),
        contains_eager(CallLog.agent)
    ).filter(
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            # Calls without both campaign and agent (edge case)
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    )

    if status:
        query = query.filter(CallLog.status == status)
    if outcome:
        query = query.filter(CallLog.outcome == outcome)
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    if agent_id:
        query = query.filter(CallLog.agent_id == agent_id)
    if date_from:
        query = query.filter(CallLog.created_at >= date_from)
    if date_to:
        query = query.filter(CallLog.created_at <= date_to)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                CallLog.customer_name.ilike(search_filter),
                CallLog.to_number.ilike(search_filter),
                CallLog.call_sid.ilike(search_filter),
            )
        )

    total = query.count()
    calls = query.order_by(CallLog.created_at.desc()).offset(skip).limit(limit).all()

    items = []
    for call in calls:
        item = {
            "id": call.id,
            "call_sid": call.call_sid,
            "provider": call.provider,
            "ultravox_call_id": call.ultravox_call_id,
            "status": call.status,
            "outcome": call.outcome,
            "duration": call.duration,
            "from_number": call.from_number,
            "to_number": call.to_number,
            "customer_name": call.customer_name,
            "started_at": call.started_at,
            "ended_at": call.ended_at,
            "connected_at": call.connected_at,
            "recording_url": call.recording_url,
            "transcription": call.transcription,
            "sentiment": call.sentiment,
            "summary": call.summary,
            "notes": call.notes,
            "intent": call.intent,
            "amd_status": call.amd_status,
            "amd_cause": call.amd_cause,
            "call_metadata": call.call_metadata,
            "campaign_id": call.campaign_id,
            "agent_id": call.agent_id,
            "agent_name": call.agent.name if call.agent else None,
            "campaign_name": call.campaign.name if call.campaign else None,
            "sip_code": call.sip_code,
            "hangup_cause": call.hangup_cause,
            "tags": call.tags,
            "model_used": call.model_used,
            "input_tokens": call.input_tokens,
            "output_tokens": call.output_tokens,
            "cached_tokens": call.cached_tokens,
            "estimated_cost": call.estimated_cost,
            "created_at": call.created_at,
        }
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
    }


@router.get("/filters")
async def get_call_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available filter options (campaigns, agents) for call log filtering"""
    campaigns = db.query(Campaign).filter(
        Campaign.owner_id == current_user.id
    ).all()
    agents = db.query(Agent).filter(
        Agent.owner_id == current_user.id
    ).all()

    return {
        "campaigns": [{"id": c.id, "name": c.name} for c in campaigns],
        "agents": [{"id": a.id, "name": a.name} for a in agents],
        "statuses": [s.value for s in CallStatus],
        "outcomes": [o.value for o in CallOutcome],
    }


@router.get("/active")
async def get_active_calls(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get currently active calls with eager loading"""
    active_statuses = [
        CallStatus.RINGING,
        CallStatus.CONNECTED,
        CallStatus.TALKING,
        CallStatus.ON_HOLD
    ]

    # Use joinedload to prevent N+1 queries
    calls = db.query(CallLog).options(
        joinedload(CallLog.campaign),
        joinedload(CallLog.agent)
    ).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        ),
        CallLog.status.in_(active_statuses)
    ).all()

    now = datetime.utcnow()

    return [
        {
            "id": call.id,
            "call_sid": call.call_sid,
            "status": call.status.value,
            "customer_name": call.customer_name,
            "to_number": call.to_number,
            "duration": int((now - call.connected_at).total_seconds()) if call.connected_at else 0,
            "campaign_id": call.campaign_id,
            "campaign_name": call.campaign.name if call.campaign else None,
            "agent_name": call.agent.name if call.agent else None,
        }
        for call in calls
    ]


@router.get("/{call_id}", response_model=CallLogResponse)
async def get_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get call details"""
    call = db.query(CallLog).options(
        joinedload(CallLog.campaign)
    ).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.id == call_id,
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    ).first()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return call


@router.get("/{call_id}/transcription")
async def get_call_transcription(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get call transcription with parsed messages.

    Returns structured transcript messages (role + content) by:
    1. Trying Redis first (available for ~1h after call ends)
    2. Falling back to DB transcription field (persisted permanently)
    """
    call = db.query(CallLog).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.id == call_id,
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    ).first()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    messages: list[dict] = []
    source = "none"

    # 1) Try Redis (structured JSON, available for recent calls)
    if redis_client and call.call_sid:
        try:
            transcript_key = f"call_transcript:{call.call_sid}"
            key_type = redis_client.type(transcript_key)
            if key_type == "list":
                raw_items = redis_client.lrange(transcript_key, 0, -1)
                for item in reversed(raw_items):
                    try:
                        entry = json.loads(item)
                        content = entry.get("content", "").strip()
                        if content:
                            messages.append({
                                "role": entry.get("role", "unknown"),
                                "content": content,
                                "timestamp": entry.get("timestamp", ""),
                            })
                    except (json.JSONDecodeError, TypeError):
                        continue
                if messages:
                    source = "redis"
        except Exception:
            pass

    # 2) Fallback: parse DB transcription field "[role]: content" format
    if not messages and call.transcription:
        import re
        for line in call.transcription.split("\n"):
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^\[(\w+)\]:\s*(.+)$", line)
            if match:
                messages.append({
                    "role": match.group(1),
                    "content": match.group(2),
                    "timestamp": "",
                })
            else:
                # Unstructured line — append as system message
                messages.append({
                    "role": "system",
                    "content": line,
                    "timestamp": "",
                })
        if messages:
            source = "database"

    return {
        "call_id": call.id,
        "call_sid": call.call_sid,
        "transcription": call.transcription,
        "messages": messages,
        "message_count": len(messages),
        "source": source,
        "sentiment": call.sentiment,
        "summary": call.summary,
        "agent_name": call.agent.name if call.agent else None,
        "customer_name": call.customer_name,
        "duration": call.duration,
        "started_at": call.started_at.isoformat() if call.started_at else None,
    }


async def _cancel_ultravox_via_ari(call: CallLog) -> bool:
    """Cancel a ringing Ultravox call by deleting the Asterisk channel via ARI.

    When Ultravox routes SIP through Asterisk, the Asterisk channel is visible
    in ARI. Deleting it sends SIP CANCEL to the trunk, immediately stopping
    the customer's phone from ringing.

    Finds the correct channel by matching the dialed number in the
    [from-ultravox] dialplan context.
    """
    import aiohttp

    phone = call.to_number
    if not phone:
        logger.warning(f"No phone number for ARI cancel, call {call.id}")
        return False

    # Normalize: strip + and leading 00
    phone = phone.lstrip("+")
    if phone.startswith("00"):
        phone = phone[2:]

    ari_url = f"http://{settings.ASTERISK_HOST}:{settings.ASTERISK_ARI_PORT}/ari"
    auth = aiohttp.BasicAuth(settings.ASTERISK_ARI_USER, settings.ASTERISK_ARI_PASSWORD)

    try:
        async with aiohttp.ClientSession(auth=auth) as session:
            # List all active Asterisk channels
            async with session.get(f"{ari_url}/channels") as resp:
                if resp.status != 200:
                    logger.error(f"ARI channels list failed: {resp.status}")
                    return False
                channels = await resp.json()

            # Find channel(s) in from-ultravox context matching the phone number
            target_channels = []
            for ch in channels:
                dialplan = ch.get("dialplan", {})
                ctx = dialplan.get("context", "")
                exten = dialplan.get("exten", "")
                ch_name = ch.get("name", "")

                # Match: from-ultravox context with matching extension
                # or any PJSIP/ultravox channel with matching number
                if ctx == "from-ultravox" and phone in exten:
                    target_channels.append(ch)
                elif "ultravox" in ch_name.lower() and phone in exten:
                    target_channels.append(ch)

            if not target_channels:
                # Also check outgoing trunk channels for this number
                for ch in channels:
                    ch_name = ch.get("name", "")
                    connected = ch.get("connected", {})
                    conn_num = connected.get("number", "")
                    if phone in ch_name or phone in conn_num:
                        target_channels.append(ch)

            if not target_channels:
                logger.warning(
                    f"No ARI channel found for Ultravox call to {phone} "
                    f"(total channels: {len(channels)})"
                )
                return False

            # Delete each matching channel — this sends SIP CANCEL
            cancelled = False
            for ch in target_channels:
                ch_id = ch["id"]
                ch_name = ch.get("name", "unknown")
                async with session.delete(f"{ari_url}/channels/{ch_id}") as del_resp:
                    if del_resp.status < 300:
                        logger.info(
                            f"ARI channel {ch_name} ({ch_id[:12]}) deleted "
                            f"— SIP CANCEL sent for {phone}"
                        )
                        cancelled = True
                    elif del_resp.status == 404:
                        logger.info(f"ARI channel {ch_id[:12]} already gone")
                        cancelled = True
                    else:
                        err = await del_resp.text()
                        logger.warning(f"ARI DELETE {ch_id[:12]} failed: {del_resp.status} {err}")

            return cancelled

    except Exception as e:
        logger.error(f"ARI cancel failed for Ultravox call to {phone}: {e}")
        return False


@router.post("/{call_id}/hangup")
async def hangup_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Forcefully end an active call"""
    from app.models.models import UserRole

    query = db.query(CallLog).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.id == call_id,
    )
    # Non-admin users can only hangup their own calls
    if current_user.role != UserRole.ADMIN:
        query = query.filter(
            or_(
                Campaign.owner_id == current_user.id,
                Agent.owner_id == current_user.id,
                (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
            )
        )
    call = query.first()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.status not in [CallStatus.RINGING, CallStatus.CONNECTED, CallStatus.TALKING]:
        raise HTTPException(status_code=400, detail="Call is not active")

    # ── Provider-specific disconnect ─────────────────────────────────────
    hangup_sent = False

    if call.provider == "ultravox" and call.ultravox_call_id:
        # Ultravox call termination strategy:
        # 1. Try send_data_message with hang_up (works for active/answered calls)
        # 2. If 422 (not joined = still ringing), use ARI to DELETE the Asterisk
        #    channel which sends SIP CANCEL → customer phone stops ringing instantly
        from app.services.ultravox_service import UltravoxService
        ultravox_svc = UltravoxService()
        try:
            result = await ultravox_svc.end_call(call.ultravox_call_id)
            if result.get("joined"):
                # Call was active and hang_up was sent — SIP BYE will be triggered
                hangup_sent = True
                logger.info(f"Ultravox hangup sent for call {call_id} (ultravox_id={call.ultravox_call_id})")
            else:
                # 422: Call was still ringing — cancel via Asterisk ARI channel DELETE
                logger.info(f"Ultravox call {call_id} still ringing, cancelling via ARI")
                hangup_sent = await _cancel_ultravox_via_ari(call)
        except Exception as e:
            logger.warning(f"Ultravox hang_up failed for call {call_id}: {e}")
            # Fallback: try ARI channel cancel
            hangup_sent = await _cancel_ultravox_via_ari(call)
    else:
        # OpenAI/xAI/Gemini+Asterisk: Redis hangup signal + ARI channel DELETE
        call_sid = call.call_sid

        # 1. Redis hangup signal (for bridge cleanup if bridge is running)
        try:
            if redis_client:
                redis_client.set(f"hangup_signal:{call_sid}", "1", ex=60)
                logger.info(f"Redis hangup signal set for call {call_id} (call_sid={call_sid[:8]})")
        except Exception as e:
            logger.warning(f"Redis hangup signal failed: {e}")

        # 2. ARI channel DELETE — terminate SIP channel directly
        # channel_id is stored in Redis by outbound_calls.py at originate time
        ari_channel_id = None
        if redis_client:
            try:
                ari_channel_id = redis_client.get(f"call_channel:{call_sid}")
            except Exception:
                pass

        if ari_channel_id:
            try:
                import aiohttp
                from app.core.config import settings as _settings
                _ari_url = f"http://{_settings.ASTERISK_HOST}:{_settings.ASTERISK_ARI_PORT}/ari/channels/{ari_channel_id}"
                _auth = aiohttp.BasicAuth(_settings.ASTERISK_ARI_USER, _settings.ASTERISK_ARI_PASSWORD)
                async with aiohttp.ClientSession(auth=_auth) as _session:
                    async with _session.delete(_ari_url) as _resp:
                        if _resp.status < 300:
                            hangup_sent = True
                            logger.info(f"ARI channel {ari_channel_id} terminated for call {call_id}")
                        elif _resp.status == 404:
                            hangup_sent = True
                            logger.info(f"ARI channel {ari_channel_id} already gone for call {call_id}")
                        else:
                            _err = await _resp.text()
                            logger.warning(f"ARI DELETE failed: {_resp.status} {_err}")
            except Exception as e:
                logger.error(f"ARI channel hangup failed for call {call_id}: {e}")
        else:
            logger.warning(f"No ARI channel_id in Redis for call_sid={call_sid[:8]}")
            hangup_sent = True  # Redis signal was sent at least

    # Set correct SIP code based on call state at hangup time
    # If the call was still RINGING (customer never answered), use 487 (Request Terminated)
    # If the call was CONNECTED/TALKING (customer answered), use 200 (Normal)
    if call.status == CallStatus.RINGING:
        if call.provider == "ultravox":
            # For Ultravox: if hangup was sent via API (joined=True), call was answered
            if hangup_sent:
                call.sip_code = 200
                call.hangup_cause = "User Hangup (Manual)"
                call.connected_at = call.connected_at or call.started_at
            else:
                call.sip_code = 487
                call.hangup_cause = "User Hangup (Manual)"
        else:
            # OpenAI/xAI/Gemini: check Redis bridge_active flag as fallback
            bridge_was_active = False
            call_sid = call.call_sid
            try:
                _r = redis.from_url(str(settings.REDIS_URL), decode_responses=True)
                bridge_was_active = bool(_r.get(f"call_bridge_active:{call_sid}"))
                _r.close()
            except Exception:
                pass

            if bridge_was_active:
                call.sip_code = 200
                call.hangup_cause = "User Hangup (Manual)"
                call.connected_at = call.connected_at or call.started_at
            else:
                call.sip_code = 487
                call.hangup_cause = "User Hangup (Manual)"
    else:
        call.sip_code = call.sip_code or 200
        call.hangup_cause = call.hangup_cause or "User Hangup (Manual)"

    call.status = CallStatus.COMPLETED
    call.ended_at = datetime.utcnow()
    if call.connected_at:
        call.duration = int((call.ended_at - call.connected_at).total_seconds())
    else:
        call.duration = 0

    # ── Immediate cost calculation for all providers ─────────────────
    # Ensures cost is available right away, webhook/bridge can refine later
    import math
    if call.duration and call.duration > 0:
        provider = call.provider or "openai"
        if provider == "ultravox":
            # Deciminute-based: $0.005 per 6-second increment
            deciminutes = math.ceil(call.duration / 6)
            call.estimated_cost = round(deciminutes * 0.005, 4)
        elif provider == "xai":
            # Per-second billing: $0.05/min
            call.estimated_cost = round(call.duration * (0.05 / 60), 4)
        elif provider in ("openai", "gemini"):
            # Token-based — try to get from Redis, else estimate from duration
            try:
                usage_data = redis_client.get(f"call_usage:{call.call_sid}") if redis_client else None
                if usage_data:
                    usage = json.loads(usage_data)
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    cached_tokens = 0
                    if provider == "openai":
                        # OpenAI Realtime mini pricing
                        input_details = usage.get("input_token_details", {})
                        cached_details = input_details.get("cached_tokens_details", {})
                        if cached_details:
                            cached_tokens = cached_details.get("text_tokens", 0) + cached_details.get("audio_tokens", 0)
                        elif input_details:
                            cached_tokens = input_details.get("cached_tokens", 0)
                        call.input_tokens = input_tokens
                        call.output_tokens = output_tokens
                        call.cached_tokens = cached_tokens
                        # Estimate: ~$0.06/min for realtime voice
                        call.estimated_cost = round(call.duration * (0.06 / 60), 4)
                    else:
                        # Gemini: ~$0.04/min estimate
                        call.input_tokens = input_tokens
                        call.output_tokens = output_tokens
                        call.estimated_cost = round(call.duration * (0.04 / 60), 4)
                else:
                    # No token data yet — duration-based estimate
                    rate_per_min = 0.06 if provider == "openai" else 0.04
                    call.estimated_cost = round(call.duration * (rate_per_min / 60), 4)
            except Exception as e:
                logger.warning(f"Cost calculation from Redis failed: {e}")
                rate_per_min = 0.06 if provider == "openai" else 0.04
                call.estimated_cost = round(call.duration * (rate_per_min / 60), 4)

        if not call.model_used and provider == "ultravox":
            call.model_used = "ultravox"

        logger.info(
            f"Hangup cost for call {call_id}: provider={provider}, "
            f"duration={call.duration}s, cost=${call.estimated_cost}"
        )

    db.commit()

    # Broadcast call update
    await connection_manager.broadcast({
        "type": "call_ended",
        "call_id": call.id,
        "status": "completed"
    })

    return {"success": True, "message": "Call ended", "hangup_sent": hangup_sent}


@router.post("/{call_id}/transfer")
async def transfer_call(
    call_id: int,
    target_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transfer an active call to another number"""
    call = db.query(CallLog).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.id == call_id,
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    ).first()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.status != CallStatus.TALKING:
        raise HTTPException(status_code=400, detail="Call is not connected")

    # TODO: Send transfer command to Asterisk via ARI

    call.status = CallStatus.TRANSFERRED
    call.transfer_reason = f"Transferred to {target_number}"
    db.commit()

    # Broadcast call update
    await connection_manager.broadcast({
        "type": "call_transferred",
        "call_id": call.id,
        "target": target_number
    })

    return {"success": True, "message": f"Call transferred to {target_number}"}


@router.post("/{call_id}/notes")
async def add_call_notes(
    call_id: int,
    notes: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add notes to a call"""
    call = db.query(CallLog).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.id == call_id,
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    ).first()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    call.notes = notes
    db.commit()

    return {"success": True, "message": "Notes added"}


# WebSocket for real-time call updates
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    token: Optional[str] = None,
):
    """
    WebSocket endpoint for real-time call updates.
    Requires JWT token via query param: ?token=<jwt>
    Includes connection limits, heartbeat, and proper cleanup.
    """
    # Validate JWT token from query params
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    if not await connection_manager.connect(websocket, client_id):
        return  # Connection rejected due to limit

    try:
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            send_heartbeat(websocket, client_id)
        )

        while True:
            try:
                # Wait for messages with timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WEBSOCKET_HEARTBEAT_INTERVAL * 2
                )

                # Parse message
                try:
                    message = json.loads(data)
                    msg_type = message.get("type", "")

                    if msg_type == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    elif msg_type == "subscribe":
                        # Handle subscription to specific campaigns/calls
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "channels": message.get("channels", [])
                        }))
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))

            except asyncio.TimeoutError:
                # Check if connection is still alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break  # Connection dead

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        heartbeat_task.cancel()
        connection_manager.disconnect(client_id)


async def send_heartbeat(websocket: WebSocket, client_id: str):
    """Send periodic heartbeat to keep connection alive"""
    try:
        while True:
            await asyncio.sleep(settings.WEBSOCKET_HEARTBEAT_INTERVAL)
            try:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
            except Exception:
                break
    except asyncio.CancelledError:
        pass


async def broadcast_call_update(call_data: dict):
    """Broadcast call update to all connected clients"""
    await connection_manager.broadcast({
        "type": "call_update",
        "data": call_data
    })


@router.get("/{call_id}/transcript")
async def get_call_transcript(
    call_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get real-time transcript for an active call.
    Retrieves transcript from Redis where asterisk-bridge stores it as a list.
    """
    if not redis_client:
        return {"transcript": [], "status": "unavailable", "message": "Redis not connected"}
    
    try:
        transcript_key = f"call_transcript:{call_id}"
        
        # Check key type - asterisk-bridge uses LPUSH (list)
        key_type = redis_client.type(transcript_key)
        
        if key_type == "list":
            # Get all items from list (newest first due to LPUSH)
            transcript_items = redis_client.lrange(transcript_key, 0, -1)
            messages = []
            for item in reversed(transcript_items):  # Reverse to get chronological order
                try:
                    msg = json.loads(item)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
            return {"transcript": messages, "status": "active", "count": len(messages)}
        
        elif key_type == "string":
            # Legacy format (backward compatibility)
            transcript_data = redis_client.get(transcript_key)
            if transcript_data:
                try:
                    messages = json.loads(transcript_data)
                    return {"transcript": messages, "status": "active"}
                except json.JSONDecodeError:
                    return {"transcript": [], "status": "error", "message": "Invalid transcript format"}
        
        # Also check for call status
        status_key = f"call_status:{call_id}"
        call_status = redis_client.get(status_key)
        
        if call_status:
            return {"transcript": [], "status": call_status}
        
        return {"transcript": [], "status": "pending", "message": "Waiting for call to connect"}
        
    except Exception as e:
        logger.error(f"Error fetching transcript for {call_id}: {e}")
        return {"transcript": [], "status": "error", "message": "Failed to retrieve transcript"}


@router.post("/{call_id}/transcript")
async def add_transcript_message(
    call_id: str,
    message: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Add a message to call transcript (for testing/simulation).
    Format: {"role": "user|assistant", "content": "message text"}
    """
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    try:
        transcript_key = f"call_transcript:{call_id}"
        
        # Get existing transcript
        existing = redis_client.get(transcript_key)
        messages = json.loads(existing) if existing else []
        
        # Add new message with timestamp
        new_message = {
            "id": str(len(messages) + 1),
            "role": message.get("role", "assistant"),
            "content": message.get("content", ""),
            "timestamp": datetime.utcnow().isoformat(),
        }
        messages.append(new_message)
        
        # Store back with 1 hour TTL
        redis_client.setex(transcript_key, 3600, json.dumps(messages))
        
        return {"success": True, "message": new_message}
        
    except Exception as e:
        logger.error(f"Error adding transcript for {call_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add transcript message")


# ============================================================================
# CALL TAGS ENDPOINTS
# ============================================================================

@router.get("/{call_id}/tags", response_model=CallTagsResponse)
async def get_call_tags(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get tags for a specific call.
    """
    call = db.query(CallLog).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.call_sid == call_id,
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return CallTagsResponse(
        call_id=call_id,
        tags=call.tags or []
    )


@router.patch("/{call_id}/tags", response_model=CallTagsResponse)
async def update_call_tags(
    call_id: str,
    tag_data: CallTagsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update tags for a specific call.
    
    Operations:
    - add: Add new tags to existing ones
    - remove: Remove specific tags
    - replace: Replace all tags with new ones
    """
    call = db.query(CallLog).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.call_sid == call_id,
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    current_tags = call.tags or []
    new_tags = [t.value if isinstance(t, CallTag) else t for t in tag_data.tags]
    
    if tag_data.operation == "add":
        # Add new tags, avoiding duplicates
        for tag in new_tags:
            if tag not in current_tags:
                current_tags.append(tag)
    elif tag_data.operation == "remove":
        # Remove specified tags
        current_tags = [t for t in current_tags if t not in new_tags]
    else:  # set
        current_tags = new_tags
    
    call.tags = current_tags
    db.commit()
    db.refresh(call)
    
    logger.info(f"Updated tags for call {call_id}: {current_tags}")
    
    return CallTagsResponse(
        call_id=call_id,
        tags=call.tags
    )


@router.get("/tags/available")
async def get_available_tags():
    """
    Get all available call tags with descriptions.
    """
    tag_descriptions = {
        "interested": "Customer showed interest",
        "not_interested": "Customer not interested",
        "callback": "Wants to be called back",
        "hot_lead": "Hot potential lead",
        "cold_lead": "Cold potential lead",
        "do_not_call": "Do not call again",
        "wrong_number": "Wrong number",
        "voicemail": "Voicemail reached",
        "busy": "Busy / Unavailable",
        "complaint": "Complaint"
    }
    
    return {
        "tags": [
            {"value": tag.value, "label": tag_descriptions.get(tag.value, tag.value)}
            for tag in CallTag
        ]
    }


# ===========================================================================
# Recording Download / Stream
# ===========================================================================

@router.get("/{call_id}/recording")
async def get_call_recording(
    call_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a presigned download URL for a call recording.
    Returns a temporary URL valid for 1 hour.
    """
    call = db.query(CallLog).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.id == call_id,
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if not call.recording_url:
        raise HTTPException(status_code=404, detail="No recording available for this call")

    from app.services.minio_service import minio_service

    # recording_url stores the MinIO key like "calls/{uuid}.wav"
    recording_key = call.recording_url
    
    # Check if the recording exists in MinIO
    if not minio_service.object_exists(settings.MINIO_BUCKET_RECORDINGS, recording_key):
        raise HTTPException(status_code=404, detail="Recording file not found in storage")

    # Generate presigned URL (1 hour expiry)
    url = minio_service.get_presigned_url(
        bucket=settings.MINIO_BUCKET_RECORDINGS,
        key=recording_key,
        expires_in=3600,
    )

    if not url:
        raise HTTPException(status_code=500, detail="Failed to generate recording URL")

    return {
        "call_id": call_id,
        "recording_url": url,
        "expires_in": 3600,
        "duration": call.recording_duration,
    }


@router.get("/{call_id}/recording/download")
async def download_call_recording(
    call_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download a call recording file directly.
    Returns the WAV file as a streaming response.
    """
    from fastapi.responses import StreamingResponse
    from app.services.minio_service import minio_service

    call = db.query(CallLog).outerjoin(CallLog.campaign).outerjoin(CallLog.agent).filter(
        CallLog.id == call_id,
        or_(
            Campaign.owner_id == current_user.id,
            Agent.owner_id == current_user.id,
            (CallLog.campaign_id.is_(None) & CallLog.agent_id.is_(None)),
        )
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.recording_url:
        raise HTTPException(status_code=404, detail="No recording available for this call")

    recording_key = call.recording_url

    # Download from MinIO
    data = minio_service.download_bytes(settings.MINIO_BUCKET_RECORDINGS, recording_key)
    if data is None:
        raise HTTPException(status_code=404, detail="Recording file not found in storage")

    # Determine filename
    filename = f"call_{call.call_sid or call_id}.wav"

    return StreamingResponse(
        iter([data]),
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )

