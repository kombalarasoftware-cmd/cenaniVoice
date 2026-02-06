from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user, verify_token
from app.models import Agent, User
from app.models.models import AgentStatus as ModelAgentStatus
from app.schemas import (
    AgentCreate, AgentUpdate, AgentResponse, AgentDetailResponse
)
from app.schemas.schemas import AgentStatus as SchemaAgentStatus

router = APIRouter(prefix="/agents", tags=["Agents"])

# Optional auth for development mode
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return default dev user"""
    if credentials:
        try:
            from jose import jwt
            payload = jwt.decode(
                credentials.credentials,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return user
        except Exception:
            pass
    
    # In dev mode, return first user as default
    if settings.DEBUG:
        default_user = db.query(User).first()
        if default_user:
            return default_user
    
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    status: Optional[ModelAgentStatus] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """List all agents for current user"""
    query = db.query(Agent).filter(Agent.owner_id == current_user.id)
    
    if status:
        query = query.filter(Agent.status == status)
    if language:
        query = query.filter(Agent.language == language)
    if search:
        query = query.filter(Agent.name.ilike(f"%{search}%"))
    
    agents = query.order_by(Agent.created_at.desc()).offset(skip).limit(limit).all()
    return agents


@router.post("", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Create a new agent"""
    agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        owner_id=current_user.id
    )
    
    # Apply voice settings
    if agent_data.voice_settings:
        agent.voice = agent_data.voice_settings.voice
        agent.language = agent_data.voice_settings.language
        agent.speech_speed = agent_data.voice_settings.speech_speed
    
    # Apply call settings
    if agent_data.call_settings:
        agent.max_duration = agent_data.call_settings.max_duration
        agent.silence_timeout = agent_data.call_settings.silence_timeout
        agent.max_retries = agent_data.call_settings.max_retries
        agent.retry_delay = agent_data.call_settings.retry_delay
    
    # Apply behavior settings
    if agent_data.behavior_settings:
        agent.interruptible = agent_data.behavior_settings.interruptible
        agent.auto_transcribe = agent_data.behavior_settings.auto_transcribe
        agent.record_calls = agent_data.behavior_settings.record_calls
        agent.human_transfer = agent_data.behavior_settings.human_transfer
    
    # Apply advanced settings
    if agent_data.advanced_settings:
        agent.temperature = agent_data.advanced_settings.temperature
        agent.vad_threshold = agent_data.advanced_settings.vad_threshold
        agent.turn_detection = agent_data.advanced_settings.turn_detection
    
    # Apply prompt sections
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
async def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get agent details"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Update an agent"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update basic fields
    if agent_data.name is not None:
        agent.name = agent_data.name
    if agent_data.description is not None:
        agent.description = agent_data.description
    if agent_data.status is not None:
        agent.status = ModelAgentStatus(agent_data.status.value)
    
    # Update voice settings
    if agent_data.voice_settings:
        agent.model_type = agent_data.voice_settings.model_type
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
    
    # Update greeting settings
    if agent_data.greeting_settings:
        agent.first_speaker = agent_data.greeting_settings.first_speaker
        agent.greeting_message = agent_data.greeting_settings.greeting_message
        agent.greeting_uninterruptible = agent_data.greeting_settings.greeting_uninterruptible
        agent.first_message_delay = agent_data.greeting_settings.first_message_delay
    
    # Update inactivity messages
    if agent_data.inactivity_messages is not None:
        agent.inactivity_messages = [msg.model_dump() for msg in agent_data.inactivity_messages]
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Delete an agent"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(agent)
    db.commit()
    
    return {"message": "Agent deleted successfully"}


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
async def duplicate_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Duplicate an agent"""
    original = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create duplicate
    duplicate = Agent(
        name=f"{original.name} (Copy)",
        description=original.description,
        status=ModelAgentStatus.DRAFT,
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
        owner_id=current_user.id
    )
    
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    
    return duplicate


@router.post("/{agent_id}/activate")
async def activate_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Activate an agent"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.status = ModelAgentStatus.ACTIVE
    db.commit()
    
    return {"message": "Agent activated"}


@router.post("/{agent_id}/deactivate")
async def deactivate_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Deactivate an agent"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.status = ModelAgentStatus.INACTIVE
    db.commit()
    
    return {"message": "Agent deactivated"}
