from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.core.voice_config import get_voices_by_provider, get_voices_by_gender
from app.api.v1.auth import get_current_user, verify_token
from app.models import Agent, User, AgentTariff
from app.models.models import AgentStatus as ModelAgentStatus, UserRole, CallLog, Campaign
from app.schemas import (
    AgentCreate, AgentUpdate, AgentResponse, AgentDetailResponse
)
from app.schemas.schemas import (
    AgentStatus as SchemaAgentStatus,
    AgentTariffCreate,
    AgentTariffUpdate,
    AgentTariffResponse,
    AgentCallLogItem,
    AgentCallLogResponse,
)

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/voices/list")
async def list_voices(
    provider: str = Query("openai", description="Provider: 'openai', 'ultravox', 'xai'"),
    gender: Optional[str] = Query(None, description="Filter by gender: 'male' or 'female'"),
    language: Optional[str] = Query(None, description="Filter by language code: 'tr', 'de', 'en', etc."),
    current_user: User = Depends(get_current_user)
):
    """List available voices for the specified provider, optionally filtered by gender/language."""
    if provider == "openai-tts":
        from app.services.cloud_tts import OPENAI_TTS_VOICES
        voices = []
        for voice_key, info in OPENAI_TTS_VOICES.items():
            gender_guess = "female" if any(w in info["label"].lower() for w in ["female", "nova", "shimmer", "coral", "sage"]) else "male"
            if gender and gender_guess != gender:
                continue
            voices.append({
                "id": voice_key,
                "name": info["label"],
                "gender": gender_guess,
                "language": info.get("lang", "multi"),
                "provider": "openai-tts",
            })
        return {"provider": "openai-tts", "voices": voices}

    if provider == "deepgram-tts":
        from app.services.cloud_tts import DEEPGRAM_TTS_VOICES
        voices = []
        for voice_key, info in DEEPGRAM_TTS_VOICES.items():
            if language and info.get("lang") != language:
                continue
            gender_guess = "female" if any(w in info["label"].lower() for w in ["female", "thalia", "andromeda", "helena"]) else "male"
            if gender and gender_guess != gender:
                continue
            voices.append({
                "id": voice_key,
                "name": info["label"],
                "gender": gender_guess,
                "language": info.get("lang", "multi"),
                "provider": "deepgram-tts",
            })
        return {"provider": "deepgram-tts", "voices": voices}

    if provider not in ("openai", "ultravox", "xai", "gemini"):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    if gender:
        voices = get_voices_by_gender(provider, gender)
    else:
        voices = get_voices_by_provider(provider)

    return {"provider": provider, "voices": voices}


@router.get("/providers/capabilities")
async def get_provider_capabilities_endpoint(
    provider: Optional[str] = Query(None, description="Specific provider name. If omitted, returns all."),
    current_user: User = Depends(get_current_user),
):
    """Return supported settings per AI provider for dynamic UI rendering."""
    from app.core.provider_capabilities import get_provider_capabilities, get_all_capabilities

    if provider:
        caps = get_provider_capabilities(provider)
        if not caps:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")
        return {provider: caps}
    return get_all_capabilities()


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
    
    # Apply call settings
    if agent_data.call_settings:
        agent.max_duration = agent_data.call_settings.max_duration
        agent.silence_timeout = agent_data.call_settings.silence_timeout
        agent.max_retries = agent_data.call_settings.max_retries
        agent.retry_delay = agent_data.call_settings.retry_delay
        agent.initial_output_medium = agent_data.call_settings.initial_output_medium
        agent.join_timeout = agent_data.call_settings.join_timeout
        if agent_data.call_settings.time_exceeded_message is not None:
            agent.time_exceeded_message = agent_data.call_settings.time_exceeded_message
    
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
        agent.prompt_language = agent_data.prompt.language
    
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
    
    # Update call settings
    if agent_data.call_settings:
        agent.max_duration = agent_data.call_settings.max_duration
        agent.silence_timeout = agent_data.call_settings.silence_timeout
        agent.max_retries = agent_data.call_settings.max_retries
        agent.retry_delay = agent_data.call_settings.retry_delay
        agent.initial_output_medium = agent_data.call_settings.initial_output_medium
        agent.join_timeout = agent_data.call_settings.join_timeout
        if agent_data.call_settings.time_exceeded_message is not None:
            agent.time_exceeded_message = agent_data.call_settings.time_exceeded_message
    
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
        agent.prompt_language = agent_data.prompt.language
    
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


# ============ Agent Tariff CRUD ============

def _get_agent_or_404(agent_id: int, db: Session, user: User) -> Agent:
    """Helper to fetch agent with ownership check."""
    if user.role == UserRole.ADMIN:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
    else:
        agent = db.query(Agent).filter(
            Agent.id == agent_id,
            (Agent.owner_id == user.id) | (Agent.is_system == True)
        ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/tariffs", response_model=List[AgentTariffResponse])
async def list_tariffs(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all tariff rules for an agent."""
    _get_agent_or_404(agent_id, db, current_user)
    tariffs = (
        db.query(AgentTariff)
        .filter(AgentTariff.agent_id == agent_id)
        .order_by(AgentTariff.prefix)
        .all()
    )
    return tariffs


@router.post("/{agent_id}/tariffs", response_model=AgentTariffResponse, status_code=201)
async def create_tariff(
    agent_id: int,
    data: AgentTariffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a tariff rule for an agent."""
    _get_agent_or_404(agent_id, db, current_user)

    # Check for duplicate prefix
    existing = (
        db.query(AgentTariff)
        .filter(AgentTariff.agent_id == agent_id, AgentTariff.prefix == data.prefix)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Prefix '{data.prefix}' already exists for this agent")

    tariff = AgentTariff(
        agent_id=agent_id,
        prefix=data.prefix,
        price_per_second=data.price_per_second,
        description=data.description,
    )
    db.add(tariff)
    db.commit()
    db.refresh(tariff)
    return tariff


@router.put("/{agent_id}/tariffs/{tariff_id}", response_model=AgentTariffResponse)
async def update_tariff(
    agent_id: int,
    tariff_id: int,
    data: AgentTariffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a tariff rule."""
    _get_agent_or_404(agent_id, db, current_user)
    tariff = (
        db.query(AgentTariff)
        .filter(AgentTariff.id == tariff_id, AgentTariff.agent_id == agent_id)
        .first()
    )
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff rule not found")

    if data.prefix is not None:
        # Check uniqueness if prefix is changing
        if data.prefix != tariff.prefix:
            dup = (
                db.query(AgentTariff)
                .filter(AgentTariff.agent_id == agent_id, AgentTariff.prefix == data.prefix)
                .first()
            )
            if dup:
                raise HTTPException(status_code=400, detail=f"Prefix '{data.prefix}' already exists")
        tariff.prefix = data.prefix
    if data.price_per_second is not None:
        tariff.price_per_second = data.price_per_second
    if data.description is not None:
        tariff.description = data.description

    db.commit()
    db.refresh(tariff)
    return tariff


@router.delete("/{agent_id}/tariffs/{tariff_id}")
async def delete_tariff(
    agent_id: int,
    tariff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a tariff rule."""
    _get_agent_or_404(agent_id, db, current_user)
    tariff = (
        db.query(AgentTariff)
        .filter(AgentTariff.id == tariff_id, AgentTariff.agent_id == agent_id)
        .first()
    )
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff rule not found")
    db.delete(tariff)
    db.commit()
    return {"message": "Tariff rule deleted"}


@router.put("/{agent_id}/tariffs", response_model=List[AgentTariffResponse])
async def bulk_update_tariffs(
    agent_id: int,
    tariffs: List[AgentTariffCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace all tariff rules for an agent (bulk save)."""
    _get_agent_or_404(agent_id, db, current_user)

    # Delete existing tariffs
    db.query(AgentTariff).filter(AgentTariff.agent_id == agent_id).delete()

    # Validate unique prefixes
    seen_prefixes: set[str] = set()
    for t in tariffs:
        if t.prefix in seen_prefixes:
            raise HTTPException(status_code=400, detail=f"Duplicate prefix '{t.prefix}' in request")
        seen_prefixes.add(t.prefix)

    # Create new tariffs
    new_tariffs = []
    for t in tariffs:
        tariff = AgentTariff(
            agent_id=agent_id,
            prefix=t.prefix,
            price_per_second=t.price_per_second,
            description=t.description,
        )
        db.add(tariff)
        new_tariffs.append(tariff)

    db.commit()
    for t in new_tariffs:
        db.refresh(t)
    return new_tariffs


# ============ Agent Call Log with Tariff Cost ============

def _match_tariff(to_number: str, tariffs: list[AgentTariff]) -> AgentTariff | None:
    """Find the tariff with the longest matching prefix for a phone number.

    Strips leading '+' before matching. Longest prefix wins (most specific).
    Example: tariffs with '49' and '495' — number '+4951234' matches '495'.
    """
    number = to_number.lstrip("+") if to_number else ""
    best: AgentTariff | None = None
    best_len = 0
    for t in tariffs:
        if number.startswith(t.prefix) and len(t.prefix) > best_len:
            best = t
            best_len = len(t.prefix)
    return best


@router.get("/call-log-all", response_model=AgentCallLogResponse)
async def all_agents_call_log(
    search: Optional[str] = Query(None, description="Search by phone number or customer name"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get call log for ALL agents owned by this user, with tariff cost."""
    from sqlalchemy import or_

    # Get all agents owned by user
    if current_user.role == UserRole.ADMIN:
        user_agents = db.query(Agent).all()
    else:
        user_agents = db.query(Agent).filter(
            or_(Agent.owner_id == current_user.id, Agent.is_system == True)
        ).all()

    agent_ids = [a.id for a in user_agents]
    agent_name_map = {a.id: a.name for a in user_agents}

    if not agent_ids:
        return AgentCallLogResponse(
            items=[], total=0, page=1, page_size=limit,
            total_duration_seconds=0, total_tariff_cost=0.0, avg_cost_per_call=0.0,
        )

    # Load tariffs for all agents
    all_tariffs = db.query(AgentTariff).filter(AgentTariff.agent_id.in_(agent_ids)).all()
    tariffs_by_agent: dict[int, list[AgentTariff]] = {}
    for t in all_tariffs:
        tariffs_by_agent.setdefault(t.agent_id, []).append(t)

    # Build query: all calls for any of the user's agents
    query = db.query(CallLog).filter(CallLog.agent_id.in_(agent_ids))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (CallLog.to_number.ilike(search_term))
            | (CallLog.customer_name.ilike(search_term))
            | (CallLog.from_number.ilike(search_term))
        )
    if date_from:
        query = query.filter(CallLog.started_at >= date_from)
    if date_to:
        query = query.filter(CallLog.started_at <= date_to)
    if status:
        query = query.filter(CallLog.status == status)
    if outcome:
        query = query.filter(CallLog.outcome == outcome)

    total = query.count()
    calls = query.order_by(CallLog.started_at.desc()).offset(skip).limit(limit).all()

    # Campaign name mapping
    campaign_ids = {c.campaign_id for c in calls if c.campaign_id}
    campaign_map: dict[int, str] = {}
    if campaign_ids:
        campaigns = db.query(Campaign.id, Campaign.name).filter(Campaign.id.in_(campaign_ids)).all()
        campaign_map = {c.id: c.name for c in campaigns}

    items: list[AgentCallLogItem] = []
    total_duration = 0
    total_tariff_cost = 0.0

    for call in calls:
        duration = call.duration or 0
        total_duration += duration

        agent_tariffs = tariffs_by_agent.get(call.agent_id, [])
        matched = _match_tariff(call.to_number or "", agent_tariffs)
        tariff_cost = None
        matched_prefix = None
        price_ps = None
        tariff_desc = None

        if matched and duration > 0:
            price_ps = matched.price_per_second
            matched_prefix = matched.prefix
            tariff_desc = matched.description
            tariff_cost = round(duration * (price_ps / 60), 6)
            total_tariff_cost += tariff_cost

        items.append(AgentCallLogItem(
            id=call.id,
            call_sid=call.call_sid,
            to_number=call.to_number,
            from_number=call.from_number,
            customer_name=call.customer_name,
            status=call.status.value if hasattr(call.status, 'value') else str(call.status),
            outcome=call.outcome.value if call.outcome and hasattr(call.outcome, 'value') else (str(call.outcome) if call.outcome else None),
            duration=duration,
            started_at=call.started_at,
            ended_at=call.ended_at,
            campaign_name=campaign_map.get(call.campaign_id) if call.campaign_id else None,
            provider=call.provider,
            matched_prefix=matched_prefix,
            price_per_second=price_ps,
            tariff_cost=tariff_cost,
            tariff_description=tariff_desc,
            agent_name=agent_name_map.get(call.agent_id),
            model_used=call.model_used,
            summary=call.summary,
            has_transcription=bool(call.transcription) or bool(call.ultravox_call_id),
        ))

    return AgentCallLogResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        total_duration_seconds=total_duration,
        total_tariff_cost=round(total_tariff_cost, 6),
        avg_cost_per_call=round(total_tariff_cost / len(items), 6) if items else 0.0,
    )


@router.get("/{agent_id}/call-log", response_model=AgentCallLogResponse)
async def agent_call_log(
    agent_id: int,
    search: Optional[str] = Query(None, description="Search by phone number or customer name"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get call log for an agent with tariff-based cost calculation.

    Cost is computed per-call using the agent's tariff rules:
    - Longest prefix match on `to_number` determines the rate
    - cost = duration_seconds * price_per_second
    """
    agent = _get_agent_or_404(agent_id, db, current_user)

    # Load tariffs for this agent (cached in memory for this request)
    tariffs = (
        db.query(AgentTariff)
        .filter(AgentTariff.agent_id == agent_id)
        .all()
    )

    # Build query
    query = db.query(CallLog).filter(CallLog.agent_id == agent_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (CallLog.to_number.ilike(search_term))
            | (CallLog.customer_name.ilike(search_term))
            | (CallLog.from_number.ilike(search_term))
        )
    if date_from:
        query = query.filter(CallLog.started_at >= date_from)
    if date_to:
        query = query.filter(CallLog.started_at <= date_to)
    if status:
        query = query.filter(CallLog.status == status)
    if outcome:
        query = query.filter(CallLog.outcome == outcome)

    total = query.count()

    calls = (
        query
        .order_by(CallLog.started_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Load campaign names in one go
    campaign_ids = {c.campaign_id for c in calls if c.campaign_id}
    campaign_map: dict[int, str] = {}
    if campaign_ids:
        campaigns = db.query(Campaign.id, Campaign.name).filter(Campaign.id.in_(campaign_ids)).all()
        campaign_map = {c.id: c.name for c in campaigns}

    # Build response items with tariff cost
    items: list[AgentCallLogItem] = []
    total_duration = 0
    total_tariff_cost = 0.0

    for call in calls:
        duration = call.duration or 0
        total_duration += duration

        matched = _match_tariff(call.to_number or "", tariffs)
        tariff_cost = None
        matched_prefix = None
        price_ps = None
        tariff_desc = None

        if matched and duration > 0:
            price_ps = matched.price_per_second
            matched_prefix = matched.prefix
            tariff_desc = matched.description
            # price_ps is per-minute rate, divide by 60 for per-second
            tariff_cost = round(duration * (price_ps / 60), 6)
            total_tariff_cost += tariff_cost

        items.append(AgentCallLogItem(
            id=call.id,
            call_sid=call.call_sid,
            to_number=call.to_number,
            from_number=call.from_number,
            customer_name=call.customer_name,
            status=call.status.value if hasattr(call.status, 'value') else str(call.status),
            outcome=call.outcome.value if call.outcome and hasattr(call.outcome, 'value') else (str(call.outcome) if call.outcome else None),
            duration=duration,
            started_at=call.started_at,
            ended_at=call.ended_at,
            campaign_name=campaign_map.get(call.campaign_id) if call.campaign_id else None,
            provider=call.provider,
            matched_prefix=matched_prefix,
            price_per_second=price_ps,
            tariff_cost=tariff_cost,
            tariff_description=tariff_desc,
            agent_name=agent.name,
            model_used=call.model_used,
            summary=call.summary,
            has_transcription=bool(call.transcription) or bool(call.ultravox_call_id),
        ))

    return AgentCallLogResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        total_duration_seconds=total_duration,
        total_tariff_cost=round(total_tariff_cost, 6),
        avg_cost_per_call=round(total_tariff_cost / len(items), 6) if items else 0.0,
    )
