"""
Campaign management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import Campaign, User, NumberList, Agent
from app.models.models import CampaignStatus
from app.schemas import CampaignCreate, CampaignUpdate, CampaignResponse

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

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
    db.commit()

    # TODO: Start Celery task for campaign execution
    # from app.tasks.celery_tasks import start_campaign_calls
    # background_tasks.add_task(start_campaign_calls.delay, campaign_id)

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

    # TODO: Pause Celery tasks

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

    # TODO: Resume Celery tasks

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
    db.commit()

    # TODO: Cancel all Celery tasks

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
