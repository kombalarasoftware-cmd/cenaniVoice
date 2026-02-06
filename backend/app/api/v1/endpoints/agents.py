"""
Agents endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Agent, AgentStatus
from app.schemas.schemas import AgentCreate, AgentUpdate, AgentResponse, AgentDetailResponse

router = APIRouter()


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[AgentStatus] = None,
    db: Session = Depends(get_db)
):
    """List all agents"""
    query = db.query(Agent)
    if status:
        query = query.filter(Agent.status == status)
    agents = query.order_by(Agent.created_at.desc()).offset(skip).limit(limit).all()
    return agents


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db)
):
    """Create a new agent"""
    # Create agent from schema
    agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        status=AgentStatus.DRAFT,
    )
    
    # Apply voice settings if provided
    if agent_data.voice_settings:
        agent.voice = agent_data.voice_settings.voice
        agent.language = agent_data.voice_settings.language
        agent.speech_speed = agent_data.voice_settings.speech_speed
    
    # Apply call settings if provided
    if agent_data.call_settings:
        agent.max_duration = agent_data.call_settings.max_duration
        agent.silence_timeout = agent_data.call_settings.silence_timeout
        agent.max_retries = agent_data.call_settings.max_retries
        agent.retry_delay = agent_data.call_settings.retry_delay
    
    # Apply behavior settings if provided
    if agent_data.behavior_settings:
        agent.interruptible = agent_data.behavior_settings.interruptible
        agent.auto_transcribe = agent_data.behavior_settings.auto_transcribe
        agent.record_calls = agent_data.behavior_settings.record_calls
        agent.human_transfer = agent_data.behavior_settings.human_transfer
    
    # Apply advanced settings if provided
    if agent_data.advanced_settings:
        agent.temperature = agent_data.advanced_settings.temperature
        agent.vad_threshold = agent_data.advanced_settings.vad_threshold
        agent.turn_detection = agent_data.advanced_settings.turn_detection
    
    # Apply prompt sections if provided
    if agent_data.prompt:
        agent.prompt_role = agent_data.prompt.role
        agent.prompt_personality = agent_data.prompt.personality
        agent.prompt_language = agent_data.prompt.language
        agent.prompt_flow = agent_data.prompt.flow
        agent.prompt_tools = agent_data.prompt.tools
        agent.prompt_safety = agent_data.prompt.safety
        agent.prompt_rules = agent_data.prompt.rules
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(agent_id: int, db: Session = Depends(get_db)):
    """Get agent by ID"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found"
        )
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    db: Session = Depends(get_db)
):
    """Update agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found"
        )
    
    # Update basic fields
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.description is not None:
        agent.description = agent_data.description
    if agent_data.status is not None:
        agent.status = agent_data.status
    
    # Update voice settings
    if agent_data.voice_settings:
        agent.voice = agent_data.voice_settings.voice
        agent.language = agent_data.voice_settings.language
        agent.speech_speed = agent_data.voice_settings.speech_speed
    
    # Update call settings
    if agent_data.call_settings:
        agent.max_duration = agent_data.call_settings.max_duration
        agent.silence_timeout = agent_data.call_settings.silence_timeout
        agent.max_retries = agent_data.call_settings.max_retries
        agent.retry_delay = agent_data.call_settings.retry_delay
    
    # Update behavior settings
    if agent_data.behavior_settings:
        agent.interruptible = agent_data.behavior_settings.interruptible
        agent.auto_transcribe = agent_data.behavior_settings.auto_transcribe
        agent.record_calls = agent_data.behavior_settings.record_calls
        agent.human_transfer = agent_data.behavior_settings.human_transfer
    
    # Update advanced settings
    if agent_data.advanced_settings:
        agent.temperature = agent_data.advanced_settings.temperature
        agent.vad_threshold = agent_data.advanced_settings.vad_threshold
        agent.turn_detection = agent_data.advanced_settings.turn_detection
    
    # Update prompt sections
    if agent_data.prompt:
        agent.prompt_role = agent_data.prompt.role
        agent.prompt_personality = agent_data.prompt.personality
        agent.prompt_language = agent_data.prompt.language
        agent.prompt_flow = agent_data.prompt.flow
        agent.prompt_tools = agent_data.prompt.tools
        agent.prompt_safety = agent_data.prompt.safety
        agent.prompt_rules = agent_data.prompt.rules
    
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    """Delete agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found"
        )
    db.delete(agent)
    db.commit()
    return None


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
async def duplicate_agent(agent_id: int, db: Session = Depends(get_db)):
    """Duplicate an agent"""
    original = db.query(Agent).filter(Agent.id == agent_id).first()
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found"
        )
    
    # Create a copy
    new_agent = Agent(
        name=f"{original.name} (Copy)",
        description=original.description,
        status=AgentStatus.DRAFT,
        voice=original.voice,
        language=original.language,
        speech_speed=original.speech_speed,
        prompt_role=original.prompt_role,
        prompt_personality=original.prompt_personality,
        prompt_language=original.prompt_language,
        prompt_flow=original.prompt_flow,
        prompt_tools=original.prompt_tools,
        prompt_safety=original.prompt_safety,
        prompt_rules=original.prompt_rules,
        max_duration=original.max_duration,
        silence_timeout=original.silence_timeout,
        max_retries=original.max_retries,
        retry_delay=original.retry_delay,
        interruptible=original.interruptible,
        auto_transcribe=original.auto_transcribe,
        record_calls=original.record_calls,
        human_transfer=original.human_transfer,
        temperature=original.temperature,
        vad_threshold=original.vad_threshold,
        turn_detection=original.turn_detection,
    )
    
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    return new_agent


@router.post("/{agent_id}/test/chat")
async def test_agent_chat(agent_id: int, db: Session = Depends(get_db)):
    """Test agent with chat (text)"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found"
        )
    return {"message": f"Chat test for agent {agent_id}", "agent_name": agent.name}


@router.post("/{agent_id}/test/phone")
async def test_agent_phone(
    agent_id: int,
    phone_number: str,
    db: Session = Depends(get_db)
):
    """Test agent with real phone call"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found"
        )
    # TODO: Trigger actual phone call via Asterisk AMI
    return {
        "message": f"Phone test initiated for agent {agent_id}",
        "agent_name": agent.name,
        "phone_number": phone_number
    }
