"""
Appointments API Endpoints

Handles appointment listing, filtering, and management.
"""

import logging
from typing import Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, or_

from app.core.database import get_db
from app.models.models import Appointment, AppointmentStatus, AppointmentType, Agent, Campaign
from app.models import User
from app.api.v1.auth import get_current_user
from app.schemas.schemas import (
    AppointmentResponse,
    AppointmentUpdate,
    AppointmentListResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/", response_model=AppointmentListResponse)
async def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[AppointmentStatus] = None,
    appointment_type: Optional[AppointmentType] = None,
    agent_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List appointments with filtering and pagination.
    
    Filters:
    - status: Filter by appointment status
    - appointment_type: Filter by type (consultation, site_visit, etc.)
    - agent_id: Filter by agent
    - campaign_id: Filter by campaign
    - date_from/date_to: Date range filter
    - search: Search in customer name/phone
    """
    query = db.query(Appointment).outerjoin(
        Agent, Appointment.agent_id == Agent.id
    ).outerjoin(
        Campaign, Appointment.campaign_id == Campaign.id
    ).filter(
        or_(
            Agent.owner_id == current_user.id,
            Campaign.owner_id == current_user.id,
            and_(Appointment.agent_id.is_(None), Appointment.campaign_id.is_(None)),
        )
    )

    # Apply filters
    if status:
        query = query.filter(Appointment.status == status)
    if appointment_type:
        query = query.filter(Appointment.appointment_type == appointment_type)
    if agent_id:
        query = query.filter(Appointment.agent_id == agent_id)
    if campaign_id:
        query = query.filter(Appointment.campaign_id == campaign_id)
    if date_from:
        query = query.filter(Appointment.appointment_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Appointment.appointment_date <= datetime.combine(date_to, datetime.max.time()))
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Appointment.customer_name.ilike(search_pattern),
                Appointment.customer_phone.ilike(search_pattern)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    query = query.order_by(Appointment.appointment_date.desc(), Appointment.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    appointments = query.all()
    
    # Build response with agent/campaign names
    items = []
    for apt in appointments:
        agent_name = None
        campaign_name = None
        
        if apt.agent_id:
            agent = db.get(Agent, apt.agent_id)
            if agent:
                agent_name = agent.name
        
        if apt.campaign_id:
            campaign = db.get(Campaign, apt.campaign_id)
            if campaign:
                campaign_name = campaign.name
        
        items.append(AppointmentResponse(
            id=apt.id,
            call_id=apt.call_id,
            agent_id=apt.agent_id,
            campaign_id=apt.campaign_id,
            customer_name=apt.customer_name,
            customer_phone=apt.customer_phone,
            customer_email=apt.customer_email,
            customer_address=apt.customer_address,
            appointment_type=apt.appointment_type,
            appointment_date=apt.appointment_date,
            appointment_time=apt.appointment_time,
            duration_minutes=apt.duration_minutes,
            status=apt.status,
            notes=apt.notes,
            location=apt.location,
            created_at=apt.created_at,
            updated_at=apt.updated_at,
            confirmed_at=apt.confirmed_at,
            agent_name=agent_name,
            campaign_name=campaign_name
        ))
    
    return AppointmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/stats")
async def get_appointment_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get appointment statistics.
    
    Returns counts by status and type.
    """
    query = db.query(Appointment)
    
    if date_from:
        query = query.filter(Appointment.appointment_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Appointment.appointment_date <= datetime.combine(date_to, datetime.max.time()))
    if agent_id:
        query = query.filter(Appointment.agent_id == agent_id)
    
    # Count by status
    status_counts = {}
    for status in AppointmentStatus:
        count = query.filter(Appointment.status == status).count()
        status_counts[status.value] = count
    
    # Count by type
    type_counts = {}
    for apt_type in AppointmentType:
        count = query.filter(Appointment.appointment_type == apt_type).count()
        type_counts[apt_type.value] = count
    
    # Today's appointments
    today = date.today()
    today_count = query.filter(
        Appointment.appointment_date >= datetime.combine(today, datetime.min.time()),
        Appointment.appointment_date <= datetime.combine(today, datetime.max.time())
    ).count()
    
    return {
        "total": query.count(),
        "today": today_count,
        "by_status": status_counts,
        "by_type": type_counts
    }


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific appointment by ID"""
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Get related names
    agent_name = None
    campaign_name = None
    
    if appointment.agent_id:
        agent = db.get(Agent, appointment.agent_id)
        if agent:
            agent_name = agent.name
    
    if appointment.campaign_id:
        campaign = db.get(Campaign, appointment.campaign_id)
        if campaign:
            campaign_name = campaign.name
    
    return AppointmentResponse(
        id=appointment.id,
        call_id=appointment.call_id,
        agent_id=appointment.agent_id,
        campaign_id=appointment.campaign_id,
        customer_name=appointment.customer_name,
        customer_phone=appointment.customer_phone,
        customer_email=appointment.customer_email,
        customer_address=appointment.customer_address,
        appointment_type=appointment.appointment_type,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status,
        notes=appointment.notes,
        location=appointment.location,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
        confirmed_at=appointment.confirmed_at,
        agent_name=agent_name,
        campaign_name=campaign_name
    )


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    update_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an appointment"""
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(appointment, field, value)
    
    db.commit()
    db.refresh(appointment)
    
    return await get_appointment(appointment_id, db)


@router.delete("/{appointment_id}")
async def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an appointment"""
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    db.delete(appointment)
    db.commit()
    
    return {"success": True, "message": "Appointment deleted"}


@router.post("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel an appointment"""
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment.status = AppointmentStatus.CANCELLED
    if reason:
        appointment.notes = f"{appointment.notes or ''}\n\nCancellation reason: {reason}".strip()
    
    db.commit()
    
    return {"success": True, "message": "Appointment cancelled"}


@router.post("/{appointment_id}/complete")
async def complete_appointment(
    appointment_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark appointment as completed"""
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment.status = AppointmentStatus.COMPLETED
    if notes:
        appointment.notes = f"{appointment.notes or ''}\n\nCompletion note: {notes}".strip()
    
    db.commit()
    
    return {"success": True, "message": "Appointment marked as completed"}
