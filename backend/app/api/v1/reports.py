from typing import Optional, List
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, Integer, cast, String as SAString, text
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import (
    User, Agent, Campaign, CallLog, CampaignStatus,
    CallStatus, CallOutcome,
    DialAttempt, DialAttemptResult, DialListEntry, CampaignList,
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
        total_agents=total_agents,
        active_calls_change=0,
        today_calls_change=0,
        success_rate_change=0,
        avg_duration_change=0
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
    current_user: User = Depends(get_current_user),
):
    """Compare costs between gpt-realtime and gpt-realtime-mini models"""
    from app.services.openai_realtime import compare_model_costs as compare_costs
    
    return compare_costs(duration_minutes * 60)


# ===================================================================
# AI Feature Reports (Sentiment, Quality Score, Tags, Callbacks, etc.)
# ===================================================================

@router.get("/ai/overview")
async def get_ai_features_overview(
    days: int = 30,
    campaign_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    AI Features Overview - Tüm yeni özelliklerin özet raporu.
    Sentiment dağılımı, ortalama quality score, tag istatistikleri,
    callback sayıları, action items.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= start_date
    )
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    if agent_id:
        query = query.filter(CallLog.agent_id == agent_id)
    
    calls = query.all()
    total = len(calls)
    
    if total == 0:
        return {
            "period_days": days,
            "total_calls": 0,
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0, "unset": 0},
            "quality_score": {"average": 0, "min": 0, "max": 0, "distribution": {}},
            "tags": {"total_unique": 0, "top_tags": []},
            "callbacks": {"total": 0, "pending": 0, "completed": 0},
            "summaries": {"with_summary": 0, "without_summary": 0},
            "satisfaction": {"positive": 0, "neutral": 0, "negative": 0},
        }
    
    # --- Sentiment Distribution ---
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0, "unset": 0}
    for c in calls:
        s = c.sentiment or "unset"
        sentiment_counts[s] = sentiment_counts.get(s, 0) + 1
    
    # --- Quality Score Stats ---
    quality_scores = []
    for c in calls:
        if c.call_metadata and isinstance(c.call_metadata, dict):
            qs = c.call_metadata.get("quality_score")
            if qs is not None:
                quality_scores.append(qs)
    
    # Quality score distribution (0-20, 21-40, 41-60, 61-80, 81-100)
    qs_dist = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for qs in quality_scores:
        if qs <= 20: qs_dist["0-20"] += 1
        elif qs <= 40: qs_dist["21-40"] += 1
        elif qs <= 60: qs_dist["41-60"] += 1
        elif qs <= 80: qs_dist["61-80"] += 1
        else: qs_dist["81-100"] += 1
    
    # --- Tags Stats ---
    tag_counter = {}
    for c in calls:
        if c.tags and isinstance(c.tags, list):
            for tag in c.tags:
                tag_counter[tag] = tag_counter.get(tag, 0) + 1
    top_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:15]
    
    # --- Callback Stats ---
    total_callbacks = sum(1 for c in calls if c.callback_scheduled is not None)
    pending_callbacks = sum(
        1 for c in calls 
        if c.callback_scheduled and c.callback_scheduled > datetime.utcnow()
    )
    completed_callbacks = total_callbacks - pending_callbacks
    
    # --- Summary Stats ---
    with_summary = sum(1 for c in calls if c.summary and len(c.summary.strip()) > 0)
    
    # --- Customer Satisfaction ---
    satisfaction_counts = {"positive": 0, "neutral": 0, "negative": 0}
    for c in calls:
        if c.call_metadata and isinstance(c.call_metadata, dict):
            sat = c.call_metadata.get("customer_satisfaction", "")
            if sat in satisfaction_counts:
                satisfaction_counts[sat] += 1
    
    return {
        "period_days": days,
        "total_calls": total,
        "sentiment": sentiment_counts,
        "quality_score": {
            "average": round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0,
            "min": min(quality_scores) if quality_scores else 0,
            "max": max(quality_scores) if quality_scores else 0,
            "total_scored": len(quality_scores),
            "distribution": qs_dist,
        },
        "tags": {
            "total_unique": len(tag_counter),
            "total_tagged_calls": sum(1 for c in calls if c.tags and len(c.tags) > 0),
            "top_tags": [{"tag": t, "count": cnt} for t, cnt in top_tags],
        },
        "callbacks": {
            "total": total_callbacks,
            "pending": pending_callbacks,
            "completed": completed_callbacks,
        },
        "summaries": {
            "with_summary": with_summary,
            "without_summary": total - with_summary,
            "coverage_percent": round(with_summary / total * 100, 1) if total > 0 else 0,
        },
        "satisfaction": satisfaction_counts,
    }


@router.get("/ai/sentiment-trend")
async def get_sentiment_trend(
    days: int = 30,
    campaign_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sentiment Trend - Günlere göre sentiment dağılımı.
    Frontend'de line/bar chart olarak gösterilir.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= start_date
    )
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    if agent_id:
        query = query.filter(CallLog.agent_id == agent_id)
    
    calls = query.order_by(CallLog.created_at).all()
    
    # Group by date
    daily = {}
    for c in calls:
        day = c.created_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "positive": 0, "neutral": 0, "negative": 0, "total": 0}
        daily[day]["total"] += 1
        s = c.sentiment or "neutral"
        if s in daily[day]:
            daily[day][s] += 1
    
    return sorted(daily.values(), key=lambda x: x["date"])


@router.get("/ai/quality-trend")
async def get_quality_score_trend(
    days: int = 30,
    campaign_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Quality Score Trend - Günlere göre ortalama quality score.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= start_date
    )
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    if agent_id:
        query = query.filter(CallLog.agent_id == agent_id)
    
    calls = query.order_by(CallLog.created_at).all()
    
    daily = {}
    for c in calls:
        day = c.created_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "scores": [], "count": 0}
        daily[day]["count"] += 1
        if c.call_metadata and isinstance(c.call_metadata, dict):
            qs = c.call_metadata.get("quality_score")
            if qs is not None:
                daily[day]["scores"].append(qs)
    
    result = []
    for day, data in sorted(daily.items()):
        scores = data["scores"]
        result.append({
            "date": data["date"],
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "total_calls": data["count"],
            "scored_calls": len(scores),
        })
    
    return result


@router.get("/ai/tags-distribution")
async def get_tags_distribution(
    days: int = 30,
    campaign_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tags Distribution - En çok kullanılan etiketler ve dağılımı.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= start_date
    )
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    if agent_id:
        query = query.filter(CallLog.agent_id == agent_id)
    
    calls = query.all()
    
    tag_counter = {}
    tag_by_sentiment = {}  # tag -> {positive: X, neutral: Y, negative: Z}
    
    for c in calls:
        if c.tags and isinstance(c.tags, list):
            for tag in c.tags:
                tag_counter[tag] = tag_counter.get(tag, 0) + 1
                if tag not in tag_by_sentiment:
                    tag_by_sentiment[tag] = {"positive": 0, "neutral": 0, "negative": 0}
                s = c.sentiment or "neutral"
                if s in tag_by_sentiment[tag]:
                    tag_by_sentiment[tag][s] += 1
    
    sorted_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    return {
        "total_unique_tags": len(tag_counter),
        "tags": [
            {
                "tag": tag,
                "count": cnt,
                "percentage": round(cnt / len(calls) * 100, 1) if calls else 0,
                "sentiment_breakdown": tag_by_sentiment.get(tag, {}),
            }
            for tag, cnt in sorted_tags
        ]
    }


@router.get("/ai/callbacks")
async def get_callback_report(
    days: int = 30,
    status: Optional[str] = Query(None, description="Filter: pending, completed, overdue, all"),
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Callback Report - Planlanan geri aramaların detaylı raporu.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    now = datetime.utcnow()
    
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
        CallLog.created_at >= start_date,
        CallLog.callback_scheduled.isnot(None)
    )
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    
    calls = query.order_by(CallLog.callback_scheduled).all()
    
    callbacks = []
    stats = {"pending": 0, "completed": 0, "overdue": 0}
    
    for c in calls:
        cb_status = "pending"
        if c.callback_scheduled < now:
            # Check if a follow-up call was made
            follow_up = db.query(CallLog).filter(
                CallLog.to_number == c.to_number,
                CallLog.created_at > c.callback_scheduled,
                CallLog.created_at >= start_date
            ).first()
            cb_status = "completed" if follow_up else "overdue"
        
        stats[cb_status] += 1
        
        # Filter by status if requested
        if status and status != "all" and cb_status != status:
            continue
        
        reason = ""
        notes = ""
        if c.call_metadata and isinstance(c.call_metadata, dict):
            reason = c.call_metadata.get("callback_reason", "")
            notes = c.call_metadata.get("callback_notes", "")
        
        callbacks.append({
            "call_id": c.id,
            "call_sid": c.call_sid,
            "customer_name": c.customer_name or "",
            "phone_number": c.to_number or c.from_number or "",
            "scheduled_at": c.callback_scheduled.isoformat() if c.callback_scheduled else None,
            "status": cb_status,
            "reason": reason,
            "notes": notes,
            "original_sentiment": c.sentiment,
            "campaign_name": c.campaign.name if c.campaign else "",
        })
    
    return {
        "stats": stats,
        "total": len(callbacks),
        "callbacks": callbacks,
    }


@router.get("/ai/call-details/{call_id}")
async def get_call_ai_details(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Single Call AI Details - Tek bir çağrının tüm AI analiz detayları.
    Quality score, sentiment, tags, summary, action items vs.
    """
    call = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.id == call_id,
        CallLog.campaign.has(owner_id=current_user.id),
    ).first()
    
    if not call:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Call not found")
    
    metadata = call.call_metadata or {}
    
    return {
        "call_id": call.id,
        "call_sid": call.call_sid,
        "customer_name": call.customer_name,
        "phone_number": call.to_number or call.from_number,
        "duration": call.duration,
        "status": call.status.value if call.status else None,
        "outcome": call.outcome.value if call.outcome else None,
        "created_at": call.created_at.isoformat(),
        "campaign_name": call.campaign.name if call.campaign else "",
        "agent_name": call.agent.name if call.agent else "",
        # AI Features
        "sentiment": call.sentiment,
        "sentiment_reason": metadata.get("sentiment_reason", ""),
        "summary": call.summary,
        "tags": call.tags or [],
        "quality_score": metadata.get("quality_score", 0),
        "customer_satisfaction": metadata.get("customer_satisfaction", ""),
        "action_items": metadata.get("action_items", []),
        "callback_scheduled": call.callback_scheduled.isoformat() if call.callback_scheduled else None,
        "callback_reason": metadata.get("callback_reason", ""),
        "callback_notes": metadata.get("callback_notes", ""),
        # Technical
        "model_used": metadata.get("model_used", call.model_used),
        "transcript_model": metadata.get("transcript_model", ""),
        "tool_calls_count": metadata.get("tool_calls_count", 0),
        "errors_count": metadata.get("errors_count", 0),
        "customer_data": metadata.get("customer_data", {}),
        # Cost
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
        "estimated_cost": call.estimated_cost,
        "transcription": call.transcription,
    }


@router.get("/ai/agent-comparison")
async def get_agent_ai_comparison(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Agent Comparison - Agent'lar arası AI metrik karşılaştırması.
    Hangi agent daha iyi sentiment, quality score, summary coverage alıyor?
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    agents = db.query(Agent).filter(Agent.owner_id == current_user.id).all()
    
    results = []
    for agent in agents:
        calls = db.query(CallLog).filter(
            CallLog.agent_id == agent.id,
            CallLog.created_at >= start_date
        ).all()
        
        total = len(calls)
        if total == 0:
            continue
        
        # Sentiment
        positive = sum(1 for c in calls if c.sentiment == "positive")
        negative = sum(1 for c in calls if c.sentiment == "negative")
        
        # Quality scores
        q_scores = []
        for c in calls:
            if c.call_metadata and isinstance(c.call_metadata, dict):
                qs = c.call_metadata.get("quality_score")
                if qs is not None:
                    q_scores.append(qs)
        
        # Summary coverage
        with_summary = sum(1 for c in calls if c.summary and len(c.summary.strip()) > 0)
        
        # Callbacks
        callbacks = sum(1 for c in calls if c.callback_scheduled is not None)
        
        # Average duration
        durations = [c.duration for c in calls if c.duration and c.duration > 0]
        avg_dur = sum(durations) / len(durations) if durations else 0
        
        results.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "total_calls": total,
            "avg_quality_score": round(sum(q_scores) / len(q_scores), 1) if q_scores else 0,
            "positive_sentiment_rate": round(positive / total * 100, 1),
            "negative_sentiment_rate": round(negative / total * 100, 1),
            "summary_coverage": round(with_summary / total * 100, 1),
            "callback_rate": round(callbacks / total * 100, 1),
            "avg_duration": round(avg_dur, 0),
        })
    
    return sorted(results, key=lambda x: x["avg_quality_score"], reverse=True)


# ===================================================================
# Phase 7 - Advanced Reporting Endpoints
# ===================================================================

@router.get("/campaigns/{campaign_id}/detailed-stats")
async def get_campaign_detailed_stats(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detailed campaign statistics: ASR, ACD, SIP code distribution, cost breakdown, calls per hour."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    calls = db.query(CallLog).filter(CallLog.campaign_id == campaign_id).all()

    total_numbers = campaign.total_numbers or 0
    dialed = len(calls)
    remaining = max(total_numbers - dialed, 0)

    # ASR = (connected / total_attempts) * 100
    connected_statuses = {CallStatus.CONNECTED, CallStatus.TALKING, CallStatus.COMPLETED}
    connected = sum(1 for c in calls if c.status in connected_statuses)
    asr = (connected / dialed * 100) if dialed > 0 else 0.0

    # ACD = average duration of connected calls
    connected_durations = [c.duration for c in calls if c.status in connected_statuses and c.duration and c.duration > 0]
    acd = sum(connected_durations) / len(connected_durations) if connected_durations else 0.0

    # SIP code distribution
    sip_distribution: dict[str, int] = {}
    for c in calls:
        code = str(c.sip_code) if c.sip_code else "unknown"
        sip_distribution[code] = sip_distribution.get(code, 0) + 1

    # Cost breakdown
    total_cost = sum(c.estimated_cost or 0.0 for c in calls)
    avg_cost = total_cost / dialed if dialed > 0 else 0.0

    # Calls per hour
    hour_counts: dict[int, int] = {}
    for c in calls:
        if c.created_at:
            h = c.created_at.hour
            hour_counts[h] = hour_counts.get(h, 0) + 1
    calls_per_hour = [{"hour": h, "count": cnt} for h, cnt in sorted(hour_counts.items())]

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "total_numbers": total_numbers,
        "dialed_count": dialed,
        "remaining": remaining,
        "asr": round(asr, 2),
        "acd": round(acd, 2),
        "sip_code_distribution": sip_distribution,
        "cost_breakdown": {
            "total_cost": round(total_cost, 4),
            "avg_cost_per_call": round(avg_cost, 4),
        },
        "calls_per_hour": calls_per_hour,
    }


@router.get("/campaigns/{campaign_id}/attempts")
async def get_campaign_attempts(
    campaign_id: int,
    result: Optional[str] = None,
    sip_code: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List dial attempts for a campaign with filtering and pagination."""
    # Verify ownership
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = db.query(DialAttempt).filter(
        DialAttempt.campaign_id == campaign_id
    )

    if result:
        query = query.filter(DialAttempt.result == result)
    if sip_code is not None:
        query = query.filter(DialAttempt.sip_code == sip_code)
    if date_from:
        query = query.filter(DialAttempt.started_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(DialAttempt.started_at <= datetime.fromisoformat(date_to))

    total = query.count()
    attempts = query.order_by(DialAttempt.started_at.desc()).offset(skip).limit(limit).all()

    items = []
    for a in attempts:
        entry = db.query(DialListEntry).filter(DialListEntry.id == a.entry_id).first()
        items.append({
            "id": a.id,
            "entry_id": a.entry_id,
            "phone_number": entry.phone_number if entry else None,
            "name": f"{entry.first_name or ''} {entry.last_name or ''}".strip() if entry else None,
            "attempt_number": a.attempt_number,
            "result": a.result,
            "sip_code": a.sip_code,
            "hangup_cause": a.hangup_cause,
            "duration": a.duration,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "ended_at": a.ended_at.isoformat() if a.ended_at else None,
        })

    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/providers/comparison")
async def get_provider_comparison(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare provider (openai vs ultravox) performance: calls, duration, success rate, cost, ASR."""
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
    )
    if date_from:
        query = query.filter(CallLog.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(CallLog.created_at <= datetime.fromisoformat(date_to))

    calls = query.all()

    providers: dict[str, dict] = {}
    for c in calls:
        p = c.provider or "openai"
        if p not in providers:
            providers[p] = {
                "total_calls": 0,
                "durations": [],
                "successes": 0,
                "costs": [],
                "connected": 0,
            }
        providers[p]["total_calls"] += 1
        if c.duration and c.duration > 0:
            providers[p]["durations"].append(c.duration)
        if c.outcome == CallOutcome.SUCCESS:
            providers[p]["successes"] += 1
        if c.estimated_cost:
            providers[p]["costs"].append(c.estimated_cost)
        connected_statuses = {CallStatus.CONNECTED, CallStatus.TALKING, CallStatus.COMPLETED}
        if c.status in connected_statuses:
            providers[p]["connected"] += 1

    result = {}
    for p, data in providers.items():
        total = data["total_calls"]
        durations = data["durations"]
        costs = data["costs"]
        result[p] = {
            "total_calls": total,
            "avg_duration": round(sum(durations) / len(durations), 2) if durations else 0,
            "success_rate": round(data["successes"] / total * 100, 2) if total > 0 else 0,
            "avg_cost": round(sum(costs) / len(costs), 4) if costs else 0,
            "asr": round(data["connected"] / total * 100, 2) if total > 0 else 0,
        }

    return result


@router.get("/sip-codes")
async def get_sip_code_distribution(
    campaign_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SIP code distribution across all calls with optional filters."""
    query = db.query(CallLog).join(CallLog.campaign).filter(
        CallLog.campaign.has(owner_id=current_user.id),
    )
    if campaign_id:
        query = query.filter(CallLog.campaign_id == campaign_id)
    if date_from:
        query = query.filter(CallLog.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(CallLog.created_at <= datetime.fromisoformat(date_to))

    calls = query.all()

    distribution: dict[str, int] = {}
    for c in calls:
        code = str(c.sip_code) if c.sip_code else "unknown"
        distribution[code] = distribution.get(code, 0) + 1

    total = sum(distribution.values())
    items = [
        {"sip_code": code, "count": cnt, "percentage": round(cnt / total * 100, 2) if total > 0 else 0}
        for code, cnt in sorted(distribution.items(), key=lambda x: x[1], reverse=True)
    ]

    return {"total_calls": total, "distribution": items}


@router.get("/export/{export_type}")
async def export_csv(
    export_type: str,
    campaign_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export calls, campaigns, or attempts as CSV download."""
    if export_type not in ("calls", "campaigns", "attempts"):
        raise HTTPException(status_code=400, detail="export_type must be 'calls', 'campaigns', or 'attempts'")

    output = io.StringIO()
    writer = csv.writer(output)

    if export_type == "calls":
        writer.writerow([
            "id", "call_sid", "provider", "status", "outcome", "duration",
            "from_number", "to_number", "customer_name", "sip_code",
            "sentiment", "estimated_cost", "created_at",
        ])
        query = db.query(CallLog).join(CallLog.campaign).filter(
            CallLog.campaign.has(owner_id=current_user.id),
        )
        if campaign_id:
            query = query.filter(CallLog.campaign_id == campaign_id)
        if date_from:
            query = query.filter(CallLog.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.filter(CallLog.created_at <= datetime.fromisoformat(date_to))

        for c in query.order_by(CallLog.created_at.desc()).all():
            writer.writerow([
                c.id, c.call_sid, c.provider,
                c.status.value if c.status else "",
                c.outcome.value if c.outcome else "",
                c.duration, c.from_number, c.to_number,
                c.customer_name, c.sip_code, c.sentiment,
                c.estimated_cost,
                c.created_at.isoformat() if c.created_at else "",
            ])

    elif export_type == "campaigns":
        writer.writerow([
            "id", "name", "status", "total_numbers", "completed_calls",
            "successful_calls", "failed_calls", "created_at",
        ])
        campaigns = db.query(Campaign).filter(
            Campaign.owner_id == current_user.id,
        ).order_by(Campaign.created_at.desc()).all()

        for camp in campaigns:
            writer.writerow([
                camp.id, camp.name,
                camp.status.value if camp.status else "",
                camp.total_numbers, camp.completed_calls,
                camp.successful_calls, camp.failed_calls,
                camp.created_at.isoformat() if camp.created_at else "",
            ])

    elif export_type == "attempts":
        writer.writerow([
            "id", "campaign_id", "phone_number", "first_name", "last_name",
            "attempt_number", "result", "sip_code", "duration", "started_at",
        ])
        query = db.query(DialAttempt)
        if campaign_id:
            query = query.filter(DialAttempt.campaign_id == campaign_id)
        if date_from:
            query = query.filter(DialAttempt.started_at >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.filter(DialAttempt.started_at <= datetime.fromisoformat(date_to))

        # Filter by ownership via campaign
        query = query.join(Campaign, DialAttempt.campaign_id == Campaign.id).filter(
            Campaign.owner_id == current_user.id,
        )

        for a in query.order_by(DialAttempt.started_at.desc()).all():
            entry = db.query(DialListEntry).filter(DialListEntry.id == a.entry_id).first()
            writer.writerow([
                a.id, a.campaign_id,
                entry.phone_number if entry else "",
                entry.first_name if entry else "",
                entry.last_name if entry else "",
                a.attempt_number, a.result, a.sip_code,
                a.duration,
                a.started_at.isoformat() if a.started_at else "",
            ])

    output.seek(0)
    filename = f"{export_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
