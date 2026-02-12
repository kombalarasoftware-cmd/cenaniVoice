from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.config import settings
from app.core.voice_config import get_voices_by_provider, get_voices_by_gender
from app.api.v1.auth import get_current_user, verify_token
from app.models import Agent, User
from app.models.models import AgentStatus as ModelAgentStatus, UserRole
from app.schemas import (
    AgentCreate, AgentUpdate, AgentResponse, AgentDetailResponse
)
from app.schemas.schemas import AgentStatus as SchemaAgentStatus

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/voices/list")
async def list_voices(
    provider: str = Query("openai", description="Provider: 'openai', 'ultravox', or 'pipeline'"),
    gender: Optional[str] = Query(None, description="Filter by gender: 'male' or 'female'"),
    language: Optional[str] = Query(None, description="Filter by language code (pipeline only): 'tr', 'de', 'en', etc."),
    current_user: User = Depends(get_current_user)
):
    """List available voices for the specified provider, optionally filtered by gender."""
    if provider == "pipeline":
        from app.services.pipeline_bridge import PIPER_AVAILABLE_VOICES
        voices = []
        for voice_id, info in PIPER_AVAILABLE_VOICES.items():
            if gender and info["gender"] != gender:
                continue
            if language and info["lang"] != language:
                continue
            voices.append({
                "id": voice_id,
                "name": info["label"],
                "gender": info["gender"],
                "language": info["lang"],
                "quality": info["quality"],
            })
        return {"provider": provider, "voices": voices}

    if provider not in ("openai", "ultravox"):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    if gender:
        voices = get_voices_by_gender(provider, gender)
    else:
        voices = get_voices_by_provider(provider)

    return {"provider": provider, "voices": voices}


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    status: Optional[ModelAgentStatus] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all agents for current user (ADMIN sees all, others see own + system)"""
    from sqlalchemy import or_
    if current_user.role == UserRole.ADMIN:
        query = db.query(Agent)
    else:
        query = db.query(Agent).filter(
            or_(
                Agent.owner_id == current_user.id,
                Agent.is_system == True
            )
        )
    
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
    current_user: User = Depends(get_current_user)
):
    """Create a new agent"""
    agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        provider=agent_data.provider or "openai",
        owner_id=current_user.id
    )
    
    # Apply voice settings
    if agent_data.voice_settings:
        agent.model_type = agent_data.voice_settings.model_type
        agent.voice = agent_data.voice_settings.voice
        agent.language = agent_data.voice_settings.language
        agent.timezone = agent_data.voice_settings.timezone
        agent.speech_speed = agent_data.voice_settings.speech_speed
        if agent_data.voice_settings.pipeline_voice is not None:
            agent.pipeline_voice = agent_data.voice_settings.pipeline_voice
    
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
        agent.vad_eagerness = agent_data.advanced_settings.vad_eagerness
        agent.silence_duration_ms = agent_data.advanced_settings.silence_duration_ms
        agent.prefix_padding_ms = agent_data.advanced_settings.prefix_padding_ms
        agent.idle_timeout_ms = agent_data.advanced_settings.idle_timeout_ms
        agent.interrupt_response = agent_data.advanced_settings.interrupt_response
        agent.create_response = agent_data.advanced_settings.create_response
        agent.noise_reduction = agent_data.advanced_settings.noise_reduction
        agent.max_output_tokens = agent_data.advanced_settings.max_output_tokens
        agent.transcript_model = agent_data.advanced_settings.transcript_model
    
    # Apply prompt sections (OpenAI Realtime Prompting Guide structure)
    if agent_data.prompt:
        agent.prompt_role = agent_data.prompt.role
        agent.prompt_personality = agent_data.prompt.personality
        agent.prompt_context = agent_data.prompt.context
        agent.prompt_pronunciations = agent_data.prompt.pronunciations
        agent.prompt_sample_phrases = agent_data.prompt.sample_phrases
        agent.prompt_tools = agent_data.prompt.tools
        agent.prompt_rules = agent_data.prompt.rules
        agent.prompt_flow = agent_data.prompt.flow
        agent.prompt_safety = agent_data.prompt.safety
        agent.prompt_language = agent_data.prompt.language  # Legacy field
    
    # Apply greeting settings
    if agent_data.greeting_settings:
        agent.first_speaker = agent_data.greeting_settings.first_speaker
        agent.greeting_message = agent_data.greeting_settings.greeting_message
        agent.greeting_uninterruptible = agent_data.greeting_settings.greeting_uninterruptible
        agent.first_message_delay = agent_data.greeting_settings.first_message_delay
    
    # Apply inactivity messages
    if agent_data.inactivity_messages is not None:
        agent.inactivity_messages = [msg.model_dump() for msg in agent_data.inactivity_messages]
    
    # Apply knowledge base
    if agent_data.knowledge_base is not None:
        agent.knowledge_base = agent_data.knowledge_base
    
    # Apply web sources
    if agent_data.web_sources is not None:
        agent.web_sources = agent_data.web_sources
    
    # Apply smart features
    if agent_data.smart_features is not None:
        agent.smart_features = agent_data.smart_features.model_dump() if hasattr(agent_data.smart_features, 'model_dump') else agent_data.smart_features
    
    # Apply survey config
    if agent_data.survey_config is not None:
        agent.survey_config = agent_data.survey_config.model_dump() if hasattr(agent_data.survey_config, 'model_dump') else agent_data.survey_config
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return agent


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get agent details (ADMIN can access any agent)"""
    if current_user.role == UserRole.ADMIN:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
    else:
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
    current_user: User = Depends(get_current_user)
):
    """Update an agent (ADMIN can update any agent)"""
    if current_user.role == UserRole.ADMIN:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
    else:
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
    if agent_data.provider is not None:
        agent.provider = agent_data.provider
    
    # Update voice settings
    if agent_data.voice_settings:
        agent.model_type = agent_data.voice_settings.model_type
        agent.voice = agent_data.voice_settings.voice
        agent.language = agent_data.voice_settings.language
        agent.timezone = agent_data.voice_settings.timezone
        agent.speech_speed = agent_data.voice_settings.speech_speed
        if agent_data.voice_settings.pipeline_voice is not None:
            agent.pipeline_voice = agent_data.voice_settings.pipeline_voice
    
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
        agent.vad_eagerness = agent_data.advanced_settings.vad_eagerness
        agent.silence_duration_ms = agent_data.advanced_settings.silence_duration_ms
        agent.prefix_padding_ms = agent_data.advanced_settings.prefix_padding_ms
        agent.idle_timeout_ms = agent_data.advanced_settings.idle_timeout_ms
        agent.interrupt_response = agent_data.advanced_settings.interrupt_response
        agent.create_response = agent_data.advanced_settings.create_response
        agent.noise_reduction = agent_data.advanced_settings.noise_reduction
        agent.max_output_tokens = agent_data.advanced_settings.max_output_tokens
        agent.transcript_model = agent_data.advanced_settings.transcript_model
    
    # Update prompt sections (OpenAI Realtime Prompting Guide structure)
    if agent_data.prompt:
        agent.prompt_role = agent_data.prompt.role
        agent.prompt_personality = agent_data.prompt.personality
        agent.prompt_context = agent_data.prompt.context
        agent.prompt_pronunciations = agent_data.prompt.pronunciations
        agent.prompt_sample_phrases = agent_data.prompt.sample_phrases
        agent.prompt_tools = agent_data.prompt.tools
        agent.prompt_rules = agent_data.prompt.rules
        agent.prompt_flow = agent_data.prompt.flow
        agent.prompt_safety = agent_data.prompt.safety
        agent.prompt_language = agent_data.prompt.language  # Legacy field
    
    # Update greeting settings
    if agent_data.greeting_settings:
        agent.first_speaker = agent_data.greeting_settings.first_speaker
        agent.greeting_message = agent_data.greeting_settings.greeting_message
        agent.greeting_uninterruptible = agent_data.greeting_settings.greeting_uninterruptible
        agent.first_message_delay = agent_data.greeting_settings.first_message_delay
    
    # Update inactivity messages
    if agent_data.inactivity_messages is not None:
        agent.inactivity_messages = [msg.model_dump() for msg in agent_data.inactivity_messages]
    
    # Update knowledge base
    if agent_data.knowledge_base is not None:
        agent.knowledge_base = agent_data.knowledge_base
    
    # Update web sources
    if agent_data.web_sources is not None:
        agent.web_sources = agent_data.web_sources
    
    # Update smart features
    if agent_data.smart_features is not None:
        agent.smart_features = agent_data.smart_features.model_dump() if hasattr(agent_data.smart_features, 'model_dump') else agent_data.smart_features
    
    # Update survey config
    if agent_data.survey_config is not None:
        agent.survey_config = agent_data.survey_config.model_dump() if hasattr(agent_data.survey_config, 'model_dump') else agent_data.survey_config
    
    db.commit()
    db.refresh(agent)
    
    return agent


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an agent (ADMIN can delete any agent)"""
    if current_user.role == UserRole.ADMIN:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
    else:
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.owner_id == current_user.id
        ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # System agents cannot be deleted
    if agent.is_system:
        raise HTTPException(
            status_code=403, 
            detail="System agents cannot be deleted."
        )
    
    db.delete(agent)
    db.commit()
    
    return {"message": "Agent deleted successfully"}


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
async def duplicate_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Duplicate an agent with all settings"""
    # System agents can be duplicated by anyone, others only by owner
    original = db.query(Agent).filter(Agent.id == agent_id).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Non-system agents can only be duplicated by owner (ADMIN can duplicate any)
    if current_user.role != UserRole.ADMIN and not original.is_system and original.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create duplicate with ALL fields
    duplicate = Agent(
        name=f"{original.name} (Copy)",
        description=original.description,
        status=ModelAgentStatus.DRAFT,
        # Provider
        provider=original.provider,
        # Model settings
        model_type=original.model_type,
        voice=original.voice,
        language=original.language,
        speech_speed=original.speech_speed,
        # Greeting settings
        first_speaker=original.first_speaker,
        greeting_message=original.greeting_message,
        greeting_uninterruptible=original.greeting_uninterruptible,
        first_message_delay=original.first_message_delay,
        inactivity_messages=original.inactivity_messages,
        # Knowledge Base & RAG
        knowledge_base_enabled=original.knowledge_base_enabled,
        knowledge_base_ids=original.knowledge_base_ids,
        knowledge_base=original.knowledge_base,
        web_sources=original.web_sources,
        # Prompt sections (all 10 sections)
        prompt_role=original.prompt_role,
        prompt_personality=original.prompt_personality,
        prompt_context=original.prompt_context,
        prompt_pronunciations=original.prompt_pronunciations,
        prompt_sample_phrases=original.prompt_sample_phrases,
        prompt_tools=original.prompt_tools,
        prompt_rules=original.prompt_rules,
        prompt_flow=original.prompt_flow,
        prompt_safety=original.prompt_safety,
        prompt_language=original.prompt_language,
        # Call settings
        max_duration=original.max_duration,
        silence_timeout=original.silence_timeout,
        max_retries=original.max_retries,
        retry_delay=original.retry_delay,
        # Behavior settings
        interruptible=original.interruptible,
        auto_transcribe=original.auto_transcribe,
        record_calls=original.record_calls,
        human_transfer=original.human_transfer,
        # Advanced settings
        temperature=original.temperature,
        vad_threshold=original.vad_threshold,
        turn_detection=original.turn_detection,
        vad_eagerness=original.vad_eagerness,
        silence_duration_ms=original.silence_duration_ms,
        prefix_padding_ms=original.prefix_padding_ms,
        idle_timeout_ms=original.idle_timeout_ms,
        interrupt_response=original.interrupt_response,
        create_response=original.create_response,
        noise_reduction=original.noise_reduction,
        max_output_tokens=original.max_output_tokens,
        transcript_model=original.transcript_model,
        # Smart features & Survey config
        smart_features=original.smart_features,
        survey_config=original.survey_config,
        # NOT copied: is_system (always False for copies)
        is_system=False,
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
    current_user: User = Depends(get_current_user)
):
    """Activate an agent (ADMIN can activate any agent)"""
    if current_user.role == UserRole.ADMIN:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
    else:
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
    current_user: User = Depends(get_current_user)
):
    """Deactivate an agent (ADMIN can deactivate any agent)"""
    if current_user.role == UserRole.ADMIN:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
    else:
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.owner_id == current_user.id
        ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.status = ModelAgentStatus.INACTIVE
    db.commit()
    
    return {"message": "Agent deactivated"}
