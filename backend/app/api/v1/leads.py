"""
Leads API Endpoints

Handles lead listing, filtering, updating, and management.
"""

import logging
from typing import Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.database import get_db
from app.models.models import Lead, LeadStatus, LeadInterestType, Agent, Campaign
from app.models import User
from app.api.v1.auth import get_current_user
from app.schemas.schemas import (
    LeadResponse,
    LeadUpdate,
    LeadListResponse,
    LeadStats
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("/", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[LeadStatus] = None,
    interest_type: Optional[LeadInterestType] = None,
    priority: Optional[int] = Query(None, ge=1, le=3),
    agent_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List leads with filtering and pagination.
    
    Filters:
    - status: Filter by lead status (new, contacted, qualified, converted, lost)
    - interest_type: Filter by interest type (callback, subscription, etc.)
    - priority: Filter by priority (1=high, 2=medium, 3=low)
    - agent_id: Filter by agent
    - campaign_id: Filter by campaign
    - date_from/date_to: Date range filter
    - search: Search in customer name/phone/email
    """
    query = db.query(Lead).outerjoin(
        Agent, Lead.agent_id == Agent.id
    ).outerjoin(
        Campaign, Lead.campaign_id == Campaign.id
    ).filter(
        or_(
            Agent.owner_id == current_user.id,
            Campaign.owner_id == current_user.id,
            and_(Lead.agent_id.is_(None), Lead.campaign_id.is_(None)),
        )
    )

    # Apply filters
    if status:
        query = query.filter(Lead.status == status)
    if interest_type:
        query = query.filter(Lead.interest_type == interest_type)
    if priority:
        query = query.filter(Lead.priority == priority)
    if agent_id:
        query = query.filter(Lead.agent_id == agent_id)
    if campaign_id:
        query = query.filter(Lead.campaign_id == campaign_id)
    if date_from:
        query = query.filter(Lead.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Lead.created_at <= datetime.combine(date_to, datetime.max.time()))
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Lead.customer_name.ilike(search_pattern),
                Lead.customer_phone.ilike(search_pattern),
                Lead.customer_email.ilike(search_pattern)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering (priority first, then date)
    query = query.order_by(Lead.priority.asc(), Lead.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    leads = query.all()
    
    # Build response with agent/campaign names
    items = []
    for lead in leads:
        agent_name = None
        campaign_name = None
        
        if lead.agent_id:
            agent = db.get(Agent, lead.agent_id)
            if agent:
                agent_name = agent.name
        
        if lead.campaign_id:
            campaign = db.get(Campaign, lead.campaign_id)
            if campaign:
                campaign_name = campaign.name
        
        items.append(LeadResponse(
            id=lead.id,
            call_id=lead.call_id,
            agent_id=lead.agent_id,
            campaign_id=lead.campaign_id,
            customer_name=lead.customer_name,
            customer_phone=lead.customer_phone,
            customer_email=lead.customer_email,
            customer_address=lead.customer_address,
            interest_type=lead.interest_type,
            customer_statement=lead.customer_statement,
            status=lead.status,
            priority=lead.priority,
            notes=lead.notes,
            source=lead.source,
            last_contacted_at=lead.last_contacted_at,
            next_follow_up=lead.next_follow_up,
            follow_up_count=lead.follow_up_count,
            converted_at=lead.converted_at,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
            agent_name=agent_name,
            campaign_name=campaign_name
        ))
    
    return LeadListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/stats", response_model=LeadStats)
async def get_lead_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    agent_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get lead statistics.
    
    Returns counts by status, interest type, and priority.
    """
    query = db.query(Lead)
    
    if date_from:
        query = query.filter(Lead.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Lead.created_at <= datetime.combine(date_to, datetime.max.time()))
    if agent_id:
        query = query.filter(Lead.agent_id == agent_id)
    if campaign_id:
        query = query.filter(Lead.campaign_id == campaign_id)
    
    # Count by status
    by_status = {}
    for status in LeadStatus:
        count = query.filter(Lead.status == status).count()
        by_status[status.value] = count
    
    # Count by interest type
    by_interest_type = {}
    for interest_type in LeadInterestType:
        count = query.filter(Lead.interest_type == interest_type).count()
        by_interest_type[interest_type.value] = count
    
    # Count by priority
    by_priority = {}
    for p in [1, 2, 3]:
        count = query.filter(Lead.priority == p).count()
        by_priority[str(p)] = count
    
    # Today's leads
    today = date.today()
    today_count = query.filter(
        Lead.created_at >= datetime.combine(today, datetime.min.time()),
        Lead.created_at <= datetime.combine(today, datetime.max.time())
    ).count()
    
    return LeadStats(
        total=query.count(),
        today=today_count,
        by_status=by_status,
        by_interest_type=by_interest_type,
        by_priority=by_priority
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific lead by ID."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    agent_name = None
    campaign_name = None
    
    if lead.agent_id:
        agent = db.get(Agent, lead.agent_id)
        if agent:
            agent_name = agent.name
    
    if lead.campaign_id:
        campaign = db.get(Campaign, lead.campaign_id)
        if campaign:
            campaign_name = campaign.name
    
    return LeadResponse(
        id=lead.id,
        call_id=lead.call_id,
        agent_id=lead.agent_id,
        campaign_id=lead.campaign_id,
        customer_name=lead.customer_name,
        customer_phone=lead.customer_phone,
        customer_email=lead.customer_email,
        customer_address=lead.customer_address,
        interest_type=lead.interest_type,
        customer_statement=lead.customer_statement,
        status=lead.status,
        priority=lead.priority,
        notes=lead.notes,
        source=lead.source,
        last_contacted_at=lead.last_contacted_at,
        next_follow_up=lead.next_follow_up,
        follow_up_count=lead.follow_up_count,
        converted_at=lead.converted_at,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        agent_name=agent_name,
        campaign_name=campaign_name
    )


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    update_data: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a lead.
    
    Can update status, priority, notes, follow-up info, etc.
    """
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Track status changes
    if "status" in update_dict:
        new_status = update_dict["status"]
        if new_status == LeadStatus.CONTACTED and not lead.last_contacted_at:
            lead.last_contacted_at = datetime.utcnow()
            lead.follow_up_count += 1
        elif new_status == LeadStatus.CONVERTED and not lead.converted_at:
            lead.converted_at = datetime.utcnow()
    
    # Apply updates
    for key, value in update_dict.items():
        setattr(lead, key, value)
    
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    
    # Get agent/campaign names
    agent_name = None
    campaign_name = None
    
    if lead.agent_id:
        agent = db.get(Agent, lead.agent_id)
        if agent:
            agent_name = agent.name
    
    if lead.campaign_id:
        campaign = db.get(Campaign, lead.campaign_id)
        if campaign:
            campaign_name = campaign.name
    
    return LeadResponse(
        id=lead.id,
        call_id=lead.call_id,
        agent_id=lead.agent_id,
        campaign_id=lead.campaign_id,
        customer_name=lead.customer_name,
        customer_phone=lead.customer_phone,
        customer_email=lead.customer_email,
        customer_address=lead.customer_address,
        interest_type=lead.interest_type,
        customer_statement=lead.customer_statement,
        status=lead.status,
        priority=lead.priority,
        notes=lead.notes,
        source=lead.source,
        last_contacted_at=lead.last_contacted_at,
        next_follow_up=lead.next_follow_up,
        follow_up_count=lead.follow_up_count,
        converted_at=lead.converted_at,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        agent_name=agent_name,
        campaign_name=campaign_name
    )


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()

    return {"message": "Lead deleted successfully", "id": lead_id}
