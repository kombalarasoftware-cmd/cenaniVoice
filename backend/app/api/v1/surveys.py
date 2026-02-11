"""
Survey API Endpoints
Anket yanıtlarını listeleme, görüntüleme ve analiz etme
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.models import (
    User, Agent, Campaign, SurveyResponse, SurveyStatus
)
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/surveys", tags=["Surveys"])


@router.get("/")
async def list_survey_responses(
    agent_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all survey responses with filtering and pagination"""
    query = db.query(SurveyResponse)
    
    # Filter by agent
    if agent_id:
        query = query.filter(SurveyResponse.agent_id == agent_id)
    
    # Filter by campaign
    if campaign_id:
        query = query.filter(SurveyResponse.campaign_id == campaign_id)
    
    # Filter by status
    if status:
        try:
            status_enum = SurveyStatus(status)
            query = query.filter(SurveyResponse.status == status_enum)
        except ValueError:
            pass
    
    # Filter by date range
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(SurveyResponse.created_at >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(SurveyResponse.created_at <= end)
        except ValueError:
            pass
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    responses = query.order_by(desc(SurveyResponse.created_at))\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    
    # Format responses
    items = []
    for resp in responses:
        agent = db.query(Agent).filter(Agent.id == resp.agent_id).first()
        items.append({
            "id": resp.id,
            "call_id": resp.call_id,
            "agent_id": resp.agent_id,
            "agent_name": agent.name if agent else None,
            "campaign_id": resp.campaign_id,
            "respondent_phone": resp.respondent_phone,
            "respondent_name": resp.respondent_name,
            "status": resp.status.value if resp.status else "unknown",
            "answers": resp.answers or [],
            "questions_answered": resp.questions_answered,
            "total_questions": resp.total_questions,
            "completion_rate": round((resp.questions_answered / resp.total_questions * 100) if resp.total_questions > 0 else 0, 1),
            "started_at": resp.started_at.isoformat() if resp.started_at else None,
            "completed_at": resp.completed_at.isoformat() if resp.completed_at else None,
            "duration_seconds": resp.duration_seconds,
            "created_at": resp.created_at.isoformat() if resp.created_at else None,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/stats")
async def get_survey_stats(
    agent_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get survey statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(SurveyResponse).filter(SurveyResponse.created_at >= start_date)
    
    if agent_id:
        query = query.filter(SurveyResponse.agent_id == agent_id)
    
    if campaign_id:
        query = query.filter(SurveyResponse.campaign_id == campaign_id)
    
    responses = query.all()
    
    # Calculate stats
    total = len(responses)
    completed = len([r for r in responses if r.status == SurveyStatus.COMPLETED])
    in_progress = len([r for r in responses if r.status == SurveyStatus.IN_PROGRESS])
    abandoned = len([r for r in responses if r.status == SurveyStatus.ABANDONED])
    
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    # Average duration for completed surveys
    completed_responses = [r for r in responses if r.status == SurveyStatus.COMPLETED and r.duration_seconds]
    total_duration = sum(r.duration_seconds or 0 for r in completed_responses)
    avg_duration = total_duration / len(completed_responses) if completed_responses else 0
    
    # Question-level stats (aggregate from all responses)
    question_stats: dict = {}
    for resp in responses:
        if resp.answers and isinstance(resp.answers, list):
            for answer in resp.answers:
                if not isinstance(answer, dict):
                    continue
                q_id = answer.get("question_id", "unknown")
                q_text = answer.get("question_text", "")
                q_type = answer.get("question_type", "")
                ans = answer.get("answer", "")
                ans_value = answer.get("answer_value")
                
                if q_id not in question_stats:
                    question_stats[q_id] = {
                        "question_id": q_id,
                        "question_text": q_text,
                        "question_type": q_type,
                        "total_answers": 0,
                        "answers": {},
                        "numeric_stats": {
                            "sum": 0,
                            "count": 0,
                            "min": None,
                            "max": None
                        }
                    }
                
                question_stats[q_id]["total_answers"] += 1
                
                # Count answer frequencies
                if ans not in question_stats[q_id]["answers"]:
                    question_stats[q_id]["answers"][ans] = 0
                question_stats[q_id]["answers"][ans] += 1
                
                # Numeric stats for rating questions
                if ans_value is not None and isinstance(ans_value, (int, float)):
                    stats = question_stats[q_id]["numeric_stats"]
                    stats["sum"] += ans_value
                    stats["count"] += 1
                    if stats["min"] is None or ans_value < stats["min"]:
                        stats["min"] = ans_value
                    if stats["max"] is None or ans_value > stats["max"]:
                        stats["max"] = ans_value
    
    # Calculate averages for numeric questions
    for q_id, stats in question_stats.items():
        num_stats = stats["numeric_stats"]
        if num_stats["count"] > 0:
            num_stats["average"] = round(num_stats["sum"] / num_stats["count"], 2)
        else:
            num_stats["average"] = None
        del num_stats["sum"]  # Remove sum from response
    
    return {
        "period_days": days,
        "total_responses": total,
        "completed": completed,
        "in_progress": in_progress,
        "abandoned": abandoned,
        "completion_rate": round(completion_rate, 1),
        "avg_duration_seconds": round(avg_duration, 1),
        "question_stats": list(question_stats.values())
    }


@router.get("/{response_id}")
async def get_survey_response(
    response_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single survey response by ID"""
    response = db.query(SurveyResponse).filter(SurveyResponse.id == response_id).first()
    
    if not response:
        raise HTTPException(status_code=404, detail="Survey response not found")
    
    agent = db.query(Agent).filter(Agent.id == response.agent_id).first()
    campaign = db.query(Campaign).filter(Campaign.id == response.campaign_id).first() if response.campaign_id else None
    
    return {
        "id": response.id,
        "call_id": response.call_id,
        "agent_id": response.agent_id,
        "agent_name": agent.name if agent else None,
        "campaign_id": response.campaign_id,
        "campaign_name": campaign.name if campaign else None,
        "respondent_phone": response.respondent_phone,
        "respondent_name": response.respondent_name,
        "status": response.status.value if response.status else "unknown",
        "answers": response.answers or [],
        "current_question_id": response.current_question_id,
        "questions_answered": response.questions_answered,
        "total_questions": response.total_questions,
        "completion_rate": round((response.questions_answered / response.total_questions * 100) if response.total_questions > 0 else 0, 1),
        "started_at": response.started_at.isoformat() if response.started_at else None,
        "completed_at": response.completed_at.isoformat() if response.completed_at else None,
        "duration_seconds": response.duration_seconds,
        "created_at": response.created_at.isoformat() if response.created_at else None,
        "updated_at": response.updated_at.isoformat() if response.updated_at else None,
    }


@router.delete("/{response_id}")
async def delete_survey_response(
    response_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a survey response"""
    response = db.query(SurveyResponse).filter(SurveyResponse.id == response_id).first()
    
    if not response:
        raise HTTPException(status_code=404, detail="Survey response not found")
    
    db.delete(response)
    db.commit()
    
    return {"message": "Survey response deleted successfully"}


@router.get("/agent/{agent_id}/summary")
async def get_agent_survey_summary(
    agent_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get survey summary for a specific agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    responses = db.query(SurveyResponse).filter(
        SurveyResponse.agent_id == agent_id,
        SurveyResponse.created_at >= start_date
    ).all()
    
    total = len(responses)
    completed = len([r for r in responses if r.status == SurveyStatus.COMPLETED])
    
    # Get survey config from agent
    survey_config = agent.survey_config if isinstance(agent.survey_config, dict) else {}
    questions = survey_config.get("questions", []) if isinstance(survey_config, dict) else []
    
    # Calculate average scores for rating questions
    rating_averages: dict = {}
    for resp in responses:
        if resp.answers and isinstance(resp.answers, list):
            for answer in resp.answers:
                if not isinstance(answer, dict):
                    continue
                q_id = answer.get("question_id")
                q_type = answer.get("question_type")
                ans_value = answer.get("answer_value")
                
                if q_type == "rating" and ans_value is not None:
                    if q_id not in rating_averages:
                        rating_averages[q_id] = {"sum": 0, "count": 0}
                    rating_averages[q_id]["sum"] += ans_value
                    rating_averages[q_id]["count"] += 1
    
    for q_id in rating_averages:
        data = rating_averages[q_id]
        rating_averages[q_id] = round(data["sum"] / data["count"], 2) if data["count"] > 0 else None
    
    # Yes/No percentages
    yes_no_stats: dict = {}
    for resp in responses:
        if resp.answers and isinstance(resp.answers, list):
            for answer in resp.answers:
                if not isinstance(answer, dict):
                    continue
                q_id = answer.get("question_id")
                q_type = answer.get("question_type")
                ans = str(answer.get("answer", "")).lower()
                
                if q_type == "yes_no":
                    if q_id not in yes_no_stats:
                        yes_no_stats[q_id] = {"yes": 0, "no": 0}
                    if ans in ["yes", "evet", "true", "1"]:
                        yes_no_stats[q_id]["yes"] += 1
                    else:
                        yes_no_stats[q_id]["no"] += 1
    
    # Calculate percentages
    for q_id in yes_no_stats:
        total_yn = yes_no_stats[q_id]["yes"] + yes_no_stats[q_id]["no"]
        if total_yn > 0:
            yes_no_stats[q_id]["yes_percent"] = round(yes_no_stats[q_id]["yes"] / total_yn * 100, 1)
            yes_no_stats[q_id]["no_percent"] = round(yes_no_stats[q_id]["no"] / total_yn * 100, 1)
    
    survey_enabled = survey_config.get("enabled", False) if isinstance(survey_config, dict) else False
    
    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "survey_enabled": survey_enabled,
        "total_questions": len(questions),
        "period_days": days,
        "total_responses": total,
        "completed_responses": completed,
        "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
        "rating_averages": rating_averages,
        "yes_no_stats": yes_no_stats
    }
