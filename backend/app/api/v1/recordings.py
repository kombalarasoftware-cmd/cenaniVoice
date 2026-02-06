from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import CallLog, User
from app.schemas import RecordingResponse

router = APIRouter(prefix="/recordings", tags=["Recordings"])


@router.get("", response_model=List[RecordingResponse])
async def list_recordings(
    campaign_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    sentiment: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List call recordings"""
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    )
    
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    if agent_id:
        query = query.filter(CallLog.agent_id == agent_id)
    if sentiment:
        query = query.filter(CallLog.sentiment == sentiment)
    if date_from:
        query = query.filter(CallLog.created_at >= date_from)
    if date_to:
        query = query.filter(CallLog.created_at <= date_to)
    if search:
        query = query.filter(
            (CallLog.customer_name.ilike(f"%{search}%")) |
            (CallLog.to_number.ilike(f"%{search}%"))
        )
    
    calls = query.order_by(CallLog.created_at.desc()).offset(skip).limit(limit).all()
    
    # Map to recording response
    recordings = []
    for call in calls:
        recordings.append(RecordingResponse(
            id=call.id,
            call_sid=call.call_sid,
            phone_number=call.to_number or "",
            customer_name=call.customer_name,
            campaign_name=call.campaign.name if call.campaign else None,
            agent_name=call.agent.name if call.agent else None,
            duration=call.recording_duration or call.duration,
            status="completed",
            sentiment=call.sentiment,
            recording_url=call.recording_url,
            transcription=call.transcription,
            created_at=call.created_at
        ))
    
    return recordings


@router.get("/{recording_id}")
async def get_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recording details"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return {
        "id": call.id,
        "call_sid": call.call_sid,
        "phone_number": call.to_number,
        "customer_name": call.customer_name,
        "campaign": {
            "id": call.campaign.id,
            "name": call.campaign.name
        } if call.campaign else None,
        "agent": {
            "id": call.agent.id,
            "name": call.agent.name
        } if call.agent else None,
        "duration": call.recording_duration or call.duration,
        "sentiment": call.sentiment,
        "intent": call.intent,
        "summary": call.summary,
        "recording_url": call.recording_url,
        "transcription": call.transcription,
        "metadata": call.metadata,
        "created_at": call.created_at
    }


@router.get("/{recording_id}/download")
async def download_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get download URL for recording"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # TODO: Generate presigned URL from MinIO
    return {
        "download_url": call.recording_url,
        "expires_in": 3600
    }


@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a recording"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # TODO: Delete from MinIO storage
    
    call.recording_url = None
    call.recording_duration = None
    db.commit()
    
    return {"message": "Recording deleted"}


@router.post("/{recording_id}/transcribe")
async def transcribe_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request transcription for a recording"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.recording_url.isnot(None)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if call.transcription:
        return {"message": "Recording already has transcription"}
    
    # TODO: Queue transcription task
    
    return {"message": "Transcription queued"}


@router.post("/{recording_id}/analyze")
async def analyze_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze recording for sentiment and intent"""
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == recording_id,
        CallLog.campaign.has(owner_id=current_user.id)
    ).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if not call.transcription:
        raise HTTPException(status_code=400, detail="No transcription available")
    
    # TODO: Queue analysis task
    
    return {"message": "Analysis queued"}
