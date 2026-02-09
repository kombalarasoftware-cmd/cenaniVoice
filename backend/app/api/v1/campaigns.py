"""
Campaign management API endpoints.
Includes background campaign execution with provider-aware call routing.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
import asyncio
import logging
import json
import os

import redis as sync_redis

from app.core.database import get_db, SessionLocal
from app.api.v1.auth import get_current_user
from app.models import Campaign, User, NumberList, Agent
from app.models.models import CampaignStatus, CallStatus, PhoneNumber, CallLog
from app.schemas import CampaignCreate, CampaignUpdate, CampaignResponse
from app.services.provider_factory import get_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
try:
    _redis = sync_redis.Redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    _redis = None

# Explicitly define which fields can be updated
ALLOWED_UPDATE_FIELDS = {
    "name",
    "description",
    "status",
    "scheduled_start",
    "call_hours_start",
    "call_hours_end",
    "concurrent_calls",
}


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[CampaignStatus] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all campaigns"""
    query = db.query(Campaign).filter(Campaign.owner_id == current_user.id)

    if status:
        query = query.filter(Campaign.status == status)
    if search:
        query = query.filter(Campaign.name.ilike(f"%{search}%"))

    campaigns = query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()
    return campaigns


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new campaign"""
    # Verify number list exists and belongs to user
    number_list = db.query(NumberList).filter(
        NumberList.id == campaign_data.number_list_id,
        NumberList.owner_id == current_user.id
    ).first()

    if not number_list:
        raise HTTPException(status_code=404, detail="Number list not found")

    # Verify agent exists and belongs to user
    agent = db.query(Agent).filter(
        Agent.id == campaign_data.agent_id,
        Agent.owner_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    campaign = Campaign(
        name=campaign_data.name,
        description=campaign_data.description,
        agent_id=campaign_data.agent_id,
        number_list_id=campaign_data.number_list_id,
        scheduled_start=campaign_data.scheduled_start,
        call_hours_start=campaign_data.call_hours_start,
        call_hours_end=campaign_data.call_hours_end,
        active_days=campaign_data.active_days,
        concurrent_calls=campaign_data.concurrent_calls,
        total_numbers=number_list.valid_numbers,
        owner_id=current_user.id
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get campaign details"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a campaign with safe field updates"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Validate status transitions
    new_status = campaign_data.status
    if new_status and campaign.status == CampaignStatus.RUNNING:
        # Can only pause a running campaign (not modify other fields)
        if new_status != CampaignStatus.PAUSED:
            raise HTTPException(
                status_code=400,
                detail="Running campaigns can only be paused. Use /stop to complete."
            )

    if campaign.status == CampaignStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Completed campaigns cannot be modified"
        )

    if campaign.status == CampaignStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Cancelled campaigns cannot be modified"
        )

    # Safely update only allowed fields
    update_data = campaign_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ALLOWED_UPDATE_FIELDS:
            setattr(campaign, field, value)
        else:
            # Log attempt to update protected field
            pass

    db.commit()
    db.refresh(campaign)

    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Cannot delete a running campaign")

    db.delete(campaign)
    db.commit()

    return {"success": True, "message": "Campaign deleted successfully"}


# =========================================================================
# Campaign execution engine (runs as a FastAPI background task)
# =========================================================================

async def _execute_campaign(campaign_id: int):
    """
    Background task that dials all numbers in a campaign's number list.

    Concurrency is controlled by asyncio.Semaphore (default: campaign.concurrent_calls).
    Pause/stop signals are communicated via Redis keys:
      - campaign_pause:{id}  -> "1"  (pause)
      - campaign_stop:{id}   -> "1"  (stop immediately)
    """
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found for execution")
            return

        agent = db.query(Agent).filter(Agent.id == campaign.agent_id).first()
        if not agent:
            logger.error(f"Agent {campaign.agent_id} not found for campaign {campaign_id}")
            campaign.status = CampaignStatus.COMPLETED
            db.commit()
            return

        provider_type = getattr(agent, "provider", "openai") or "openai"
        provider = get_provider(provider_type)

        # Fetch uncalled phone numbers from the number list
        phones = (
            db.query(PhoneNumber)
            .filter(
                PhoneNumber.number_list_id == campaign.number_list_id,
                PhoneNumber.is_valid == True,
                PhoneNumber.call_attempts == 0,
            )
            .all()
        )

        if not phones:
            logger.info(f"Campaign {campaign_id}: no numbers to dial")
            campaign.status = CampaignStatus.COMPLETED
            db.commit()
            return

        max_concurrent = campaign.concurrent_calls or 10
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _dial_one(phone_record: PhoneNumber):
            """Dial a single number under semaphore control."""
            async with semaphore:
                # Check pause / stop signals
                if _redis:
                    if _redis.get(f"campaign_stop:{campaign_id}"):
                        return
                    while _redis.get(f"campaign_pause:{campaign_id}"):
                        await asyncio.sleep(2)

                phone_number = phone_record.phone.lstrip("+").replace(" ", "")
                customer_name = phone_record.name or ""

                try:
                    # Update active count atomically
                    db.execute(
                        text("UPDATE campaigns SET active_calls = active_calls + 1 WHERE id = :cid"),
                        {"cid": campaign.id}
                    )
                    db.commit()

                    result = await provider.initiate_call(
                        agent=agent,
                        phone_number=phone_number,
                        caller_id=agent.caller_id if hasattr(agent, "caller_id") and agent.caller_id else phone_number,
                        customer_name=customer_name,
                        customer_title="",
                        conversation_history="",
                        variables={"campaign_id": str(campaign_id)},
                    )

                    # Create CallLog
                    call_log = CallLog(
                        call_sid=result.get("call_id", ""),
                        provider=provider_type,
                        ultravox_call_id=result.get("ultravox_call_id"),
                        status=CallStatus.RINGING,
                        to_number=phone_number,
                        from_number=result.get("caller_id", ""),
                        customer_name=customer_name or None,
                        agent_id=agent.id,
                        campaign_id=campaign.id,
                        started_at=datetime.utcnow(),
                    )
                    db.add(call_log)

                    phone_record.call_attempts += 1
                    phone_record.last_call_at = datetime.utcnow()

                    # Update campaign stats atomically
                    db.execute(
                        text("""
                        UPDATE campaigns
                        SET completed_calls = COALESCE(completed_calls, 0) + 1,
                            successful_calls = COALESCE(successful_calls, 0) + 1,
                            active_calls = GREATEST(COALESCE(active_calls, 1) - 1, 0)
                        WHERE id = :cid
                        """),
                        {"cid": campaign.id}
                    )
                    db.commit()

                    logger.info(f"Campaign {campaign_id}: dialled {phone_number} -> {result.get('call_id', '?')}")

                except Exception as e:
                    logger.error(f"Campaign {campaign_id}: failed to dial {phone_number}: {e}")
                    phone_record.call_attempts += 1
                    # Update campaign stats atomically
                    db.execute(
                        text("""
                        UPDATE campaigns
                        SET failed_calls = COALESCE(failed_calls, 0) + 1,
                            active_calls = GREATEST(COALESCE(active_calls, 1) - 1, 0)
                        WHERE id = :cid
                        """),
                        {"cid": campaign.id}
                    )
                    db.commit()

        # Run all calls concurrently (semaphore limits parallelism)
        tasks = [asyncio.create_task(_dial_one(p)) for p in phones]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Mark campaign complete (unless already stopped/cancelled)
        db.refresh(campaign)
        if campaign.status == CampaignStatus.RUNNING:
            campaign.status = CampaignStatus.COMPLETED
            campaign.active_calls = 0
            db.commit()

        # Clean up Redis signals
        if _redis:
            _redis.delete(f"campaign_pause:{campaign_id}", f"campaign_stop:{campaign_id}")

        logger.info(f"Campaign {campaign_id} execution finished")

    except Exception as e:
        logger.error(f"Campaign {campaign_id} execution error: {e}")
        try:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if campaign and campaign.status == CampaignStatus.RUNNING:
                campaign.status = CampaignStatus.PAUSED
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Campaign is already running")

    if campaign.status == CampaignStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Campaign is already completed")

    if campaign.status == CampaignStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Campaign is cancelled")

    # Verify agent is active
    if campaign.agent and campaign.agent.status.value != "active":
        raise HTTPException(status_code=400, detail="Agent must be active to start campaign")

    campaign.status = CampaignStatus.RUNNING
    campaign.active_calls = 0
    db.commit()

    # Clear any leftover signals from a previous run
    if _redis:
        _redis.delete(f"campaign_pause:{campaign_id}", f"campaign_stop:{campaign_id}")

    # Launch campaign execution as a background task
    background_tasks.add_task(_execute_campaign, campaign_id)

    return {"success": True, "message": "Campaign started", "status": "running"}


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause a campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Campaign is not running")

    campaign.status = CampaignStatus.PAUSED
    db.commit()

    # Signal the background execution loop to pause
    if _redis:
        _redis.setex(f"campaign_pause:{campaign_id}", 3600, "1")

    return {"success": True, "message": "Campaign paused"}


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused campaign"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Campaign is not paused")

    campaign.status = CampaignStatus.RUNNING
    db.commit()

    # Remove pause signal so the background loop continues
    if _redis:
        _redis.delete(f"campaign_pause:{campaign_id}")

    return {"success": True, "message": "Campaign resumed"}


@router.post("/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stop a campaign completely"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in [CampaignStatus.RUNNING, CampaignStatus.PAUSED]:
        raise HTTPException(status_code=400, detail="Campaign is not active")

    campaign.status = CampaignStatus.COMPLETED
    campaign.active_calls = 0
    db.commit()

    # Signal the background loop to stop immediately
    if _redis:
        _redis.setex(f"campaign_stop:{campaign_id}", 3600, "1")
        _redis.delete(f"campaign_pause:{campaign_id}")

    return {"success": True, "message": "Campaign stopped"}


@router.post("/{campaign_id}/cancel")
async def cancel_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a campaign (different from stop - marks as cancelled)"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == CampaignStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed campaign")

    if campaign.status == CampaignStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Campaign is already cancelled")

    campaign.status = CampaignStatus.CANCELLED
    db.commit()

    return {"success": True, "message": "Campaign cancelled"}


@router.get("/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get campaign statistics"""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    completed = campaign.completed_calls
    total = campaign.total_numbers

    return {
        "total_numbers": total,
        "completed_calls": completed,
        "successful_calls": campaign.successful_calls,
        "failed_calls": campaign.failed_calls,
        "active_calls": campaign.active_calls,
        "remaining_calls": max(0, total - completed),
        "success_rate": round((campaign.successful_calls / completed * 100), 2) if completed > 0 else 0,
        "progress": round((completed / total * 100), 2) if total > 0 else 0
    }
