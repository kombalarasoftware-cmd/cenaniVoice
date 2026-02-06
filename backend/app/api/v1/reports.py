from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, Integer
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import (
    User, Agent, Campaign, CallLog, CampaignStatus, 
    CallStatus, CallOutcome
)
from app.schemas import DashboardStats, CallStats

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Active calls
    active_statuses = [CallStatus.RINGING, CallStatus.CONNECTED, CallStatus.TALKING]
    active_calls = db.query(func.count(CallLog.id)).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.status.in_(active_statuses)
    ).scalar()
    
    # Today's calls
    today_calls = db.query(func.count(CallLog.id)).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= today
    ).scalar()
    
    # Success rate (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    total_completed = db.query(func.count(CallLog.id)).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.status == CallStatus.COMPLETED,
        CallLog.created_at >= week_ago
    ).scalar()
    
    successful = db.query(func.count(CallLog.id)).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.outcome == CallOutcome.SUCCESS,
        CallLog.created_at >= week_ago
    ).scalar()
    
    success_rate = (successful / total_completed * 100) if total_completed > 0 else 0
    
    # Average duration
    avg_duration = db.query(func.avg(CallLog.duration)).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.duration > 0
    ).scalar() or 0
    
    # Active campaigns
    active_campaigns = db.query(func.count(Campaign.id)).filter(
        Campaign.owner_id == current_user.id,
        Campaign.status == CampaignStatus.RUNNING
    ).scalar()
    
    # Total agents
    total_agents = db.query(func.count(Agent.id)).filter(
        Agent.owner_id == current_user.id
    ).scalar()
    
    return DashboardStats(
        active_calls=active_calls,
        today_calls=today_calls,
        success_rate=round(success_rate, 1),
        avg_duration=round(avg_duration, 0),
        active_campaigns=active_campaigns,
        total_agents=total_agents
    )


@router.get("/calls/stats")
async def get_call_stats(
    days: int = 7,
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed call statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= start_date
    )
    
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    
    calls = query.all()
    
    # Calculate stats
    total = len(calls)
    successful = sum(1 for c in calls if c.outcome == CallOutcome.SUCCESS)
    failed = sum(1 for c in calls if c.outcome == CallOutcome.FAILED)
    transferred = sum(1 for c in calls if c.outcome == CallOutcome.TRANSFERRED)
    no_answer = sum(1 for c in calls if c.outcome == CallOutcome.NO_ANSWER)
    
    durations = [c.duration for c in calls if c.duration and c.duration > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "transferred": transferred,
        "no_answer": no_answer,
        "avg_duration": round(avg_duration, 0),
        "success_rate": round((successful / total * 100) if total > 0 else 0, 1)
    }


@router.get("/calls/by-day")
async def get_calls_by_day(
    days: int = 30,
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get calls grouped by day"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(
        func.date(CallLog.created_at).label('date'),
        func.count(CallLog.id).label('total'),
        func.sum(
            case((CallLog.outcome == CallOutcome.SUCCESS, 1), else_=0)
        ).label('successful')
    ).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= start_date
    ).group_by(func.date(CallLog.created_at)).order_by('date')
    
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    
    results = query.all()
    
    return [
        {
            "date": r.date.isoformat(),
            "total": r.total,
            "successful": r.successful or 0
        }
        for r in results
    ]


@router.get("/calls/by-hour")
async def get_calls_by_hour(
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get calls grouped by hour of day"""
    query = db.query(
        func.extract('hour', CallLog.created_at).label('hour'),
        func.count(CallLog.id).label('total'),
        func.avg(
            case((CallLog.outcome == CallOutcome.SUCCESS, 1), else_=0)
        ).label('success_rate')
    ).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id)
    ).group_by('hour').order_by('hour')
    
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    
    results = query.all()
    
    return [
        {
            "hour": int(r.hour),
            "total": r.total,
            "success_rate": round((r.success_rate or 0) * 100, 1)
        }
        for r in results
    ]


@router.get("/campaigns/performance")
async def get_campaign_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for all campaigns"""
    campaigns = db.query(Campaign).filter(
        Campaign.owner_id == current_user.id
    ).all()
    
    results = []
    for campaign in campaigns:
        progress = (campaign.completed_calls / campaign.total_numbers * 100) if campaign.total_numbers > 0 else 0
        success_rate = (campaign.successful_calls / campaign.completed_calls * 100) if campaign.completed_calls > 0 else 0
        
        results.append({
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status.value,
            "total_numbers": campaign.total_numbers,
            "completed_calls": campaign.completed_calls,
            "successful_calls": campaign.successful_calls,
            "progress": round(progress, 1),
            "success_rate": round(success_rate, 1)
        })
    
    return results


@router.get("/agents/performance")
async def get_agent_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for all agents"""
    agents = db.query(Agent).filter(
        Agent.owner_id == current_user.id
    ).all()
    
    results = []
    for agent in agents:
        success_rate = (agent.successful_calls / agent.total_calls * 100) if agent.total_calls > 0 else 0
        
        results.append({
            "id": agent.id,
            "name": agent.name,
            "status": agent.status.value,
            "total_calls": agent.total_calls,
            "successful_calls": agent.successful_calls,
            "avg_duration": round(agent.avg_duration, 0),
            "success_rate": round(success_rate, 1)
        })
    
    return results


@router.get("/costs/summary")
async def get_cost_summary(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get cost summary for OpenAI Realtime API usage"""
    from datetime import datetime, timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Query call logs with cost data
    call_logs = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= start_date
    ).all()
    
    # Aggregate by model
    model_breakdown = {}
    total_input = 0
    total_output = 0
    total_cached = 0
    total_cost = 0.0
    total_duration = 0
    
    for log in call_logs:
        model = log.model_used or "gpt-realtime-mini"
        
        if model not in model_breakdown:
            model_breakdown[model] = {
                "call_count": 0,
                "duration_seconds": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_tokens": 0,
                "cost_usd": 0.0,
            }
        
        model_breakdown[model]["call_count"] += 1
        model_breakdown[model]["duration_seconds"] += log.duration or 0
        model_breakdown[model]["input_tokens"] += log.input_tokens or 0
        model_breakdown[model]["output_tokens"] += log.output_tokens or 0
        model_breakdown[model]["cached_tokens"] += log.cached_tokens or 0
        model_breakdown[model]["cost_usd"] += log.estimated_cost or 0.0
        
        total_input += log.input_tokens or 0
        total_output += log.output_tokens or 0
        total_cached += log.cached_tokens or 0
        total_cost += log.estimated_cost or 0.0
        total_duration += log.duration or 0
    
    total_calls = len(call_logs)
    
    return {
        "period_days": days,
        "total_calls": total_calls,
        "total_duration_seconds": total_duration,
        "total_duration_hours": round(total_duration / 3600, 2),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cached_tokens": total_cached,
        "total_cost_usd": round(total_cost, 4),
        "avg_cost_per_call": round(total_cost / total_calls, 4) if total_calls > 0 else 0,
        "avg_cost_per_minute": round(total_cost / (total_duration / 60), 4) if total_duration > 0 else 0,
        "model_breakdown": model_breakdown,
    }


@router.get("/costs/comparison")
async def compare_model_costs(
    duration_minutes: int = 5,
):
    """Compare costs between gpt-realtime and gpt-realtime-mini models"""
    from app.services.openai_realtime import compare_model_costs as compare_costs
    
    return compare_costs(duration_minutes * 60)
