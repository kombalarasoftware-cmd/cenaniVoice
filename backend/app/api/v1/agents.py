from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user, verify_token, get_current_user_optional
from app.models import Agent, User
from app.models.models import AgentStatus as ModelAgentStatus
from app.schemas import (
    AgentCreate, AgentUpdate, AgentResponse, AgentDetailResponse
)
from app.schemas.schemas import AgentStatus as SchemaAgentStatus

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/voices/list")
async def list_voices(
    provider: str = Query("openai", description="Provider: 'openai' or 'ultravox'"),
    current_user: User = Depends(get_current_user_optional)
):
    """List available voices for the specified provider."""
    if provider == "openai":
        return {
            "provider": "openai",
            "voices": [
                {"id": "alloy", "name": "Alloy", "gender": "neutral"},
                {"id": "ash", "name": "Ash", "gender": "male"},
                {"id": "ballad", "name": "Ballad", "gender": "female"},
                {"id": "coral", "name": "Coral", "gender": "female"},
                {"id": "echo", "name": "Echo", "gender": "male"},
                {"id": "sage", "name": "Sage", "gender": "female"},
                {"id": "shimmer", "name": "Shimmer", "gender": "female"},
                {"id": "verse", "name": "Verse", "gender": "male"},
            ]
        }
    elif provider == "ultravox":
        # Try to fetch from Ultravox API, fall back to known voices
        try:
            from app.services.ultravox_service import UltravoxService
            service = UltravoxService()
            voices = await service.list_voices()
            return {"provider": "ultravox", "voices": voices}
        except Exception:
            return {
                "provider": "ultravox",
                "voices": [
                    # Turkish
                    {"id": "Cicek-Turkish", "name": "Cicek", "gender": "female", "language": "tr"},
                    {"id": "Doga-Turkish", "name": "Doga", "gender": "male", "language": "tr"},
                    # English
                    {"id": "Mark", "name": "Mark", "gender": "male", "language": "en"},
                    {"id": "Jessica", "name": "Jessica", "gender": "female", "language": "en"},
                    {"id": "Sarah", "name": "Sarah", "gender": "female", "language": "en"},
                    {"id": "Alex", "name": "Alex", "gender": "male", "language": "en"},
                    {"id": "Carter", "name": "Carter", "gender": "male", "language": "en"},
                    {"id": "Olivia", "name": "Olivia", "gender": "female", "language": "en"},
                    {"id": "Edward", "name": "Edward", "gender": "male", "language": "en"},
                    {"id": "Luna", "name": "Luna", "gender": "female", "language": "en"},
                    {"id": "Ashley", "name": "Ashley", "gender": "female", "language": "en"},
                    {"id": "Dennis", "name": "Dennis", "gender": "male", "language": "en"},
                    {"id": "Theodore", "name": "Theodore", "gender": "male", "language": "en"},
                    {"id": "Julia", "name": "Julia", "gender": "female", "language": "en"},
                    {"id": "Shaun", "name": "Shaun", "gender": "male", "language": "en"},
                    {"id": "Hana", "name": "Hana", "gender": "female", "language": "en"},
                    {"id": "Blake", "name": "Blake", "gender": "male", "language": "en"},
                    {"id": "Timothy", "name": "Timothy", "gender": "male", "language": "en"},
                    {"id": "Priya", "name": "Priya", "gender": "female", "language": "en"},
                    {"id": "Chelsea", "name": "Chelsea", "gender": "female", "language": "en"},
                    {"id": "Emily-English", "name": "Emily", "gender": "female", "language": "en"},
                    {"id": "Aaron-English", "name": "Aaron", "gender": "male", "language": "en"},
                    # German
                    {"id": "Josef", "name": "Josef", "gender": "male", "language": "de"},
                    {"id": "Johanna", "name": "Johanna", "gender": "female", "language": "de"},
                    {"id": "Ben-German", "name": "Ben", "gender": "male", "language": "de"},
                    {"id": "Frida - German", "name": "Frida", "gender": "female", "language": "de"},
                    {"id": "Susi-German", "name": "Susi", "gender": "female", "language": "de"},
                    # French
                    {"id": "Hugo-French", "name": "Hugo", "gender": "male", "language": "fr"},
                    {"id": "Coco-French", "name": "Coco", "gender": "female", "language": "fr"},
                    {"id": "Gabriel-French", "name": "Gabriel", "gender": "male", "language": "fr"},
                    {"id": "Alize-French", "name": "Alize", "gender": "female", "language": "fr"},
                    {"id": "Nicolas-French", "name": "Nicolas", "gender": "male", "language": "fr"},
                    # Spanish
                    {"id": "Alex-Spanish", "name": "Alex", "gender": "male", "language": "es"},
                    {"id": "Andrea-Spanish", "name": "Andrea", "gender": "female", "language": "es"},
                    {"id": "Damian-Spanish", "name": "Damian", "gender": "male", "language": "es"},
                    {"id": "Tatiana-Spanish", "name": "Tatiana", "gender": "female", "language": "es"},
                    {"id": "Mauricio-Spanish", "name": "Mauricio", "gender": "male", "language": "es"},
                    # Italian
                    {"id": "Linda-Italian", "name": "Linda", "gender": "female", "language": "it"},
                    {"id": "Giovanni-Italian", "name": "Giovanni", "gender": "male", "language": "it"},
                    # Portuguese
                    {"id": "Rosa-Portuguese", "name": "Rosa", "gender": "female", "language": "pt-BR"},
                    {"id": "Tiago-Portuguese", "name": "Tiago", "gender": "male", "language": "pt-BR"},
                    {"id": "Samuel-Portuguese", "name": "Samuel", "gender": "male", "language": "pt-PT"},
                    # Arabic
                    {"id": "Salma-Arabic", "name": "Salma", "gender": "female", "language": "ar"},
                    {"id": "Raed-Arabic", "name": "Raed", "gender": "male", "language": "ar-SA"},
                    {"id": "Anas-Arabic", "name": "Anas", "gender": "male", "language": "ar"},
                    # Japanese
                    {"id": "Morioki-Japanese", "name": "Morioki", "gender": "male", "language": "ja"},
                    {"id": "Asahi-Japanese", "name": "Asahi", "gender": "female", "language": "ja"},
                    # Korean
                    {"id": "Yoona", "name": "Yoona", "gender": "female", "language": "ko"},
                    {"id": "Seojun", "name": "Seojun", "gender": "male", "language": "ko"},
                    # Chinese
                    {"id": "Maya-Chinese", "name": "Maya", "gender": "female", "language": "zh"},
                    {"id": "Martin-Chinese", "name": "Martin", "gender": "male", "language": "zh"},
                    # Hindi
                    {"id": "Riya-Hindi-Urdu", "name": "Riya", "gender": "female", "language": "hi"},
                    {"id": "Aakash-Hindi", "name": "Aakash", "gender": "male", "language": "hi"},
                    # Russian
                    {"id": "Nadia-Russian", "name": "Nadia", "gender": "female", "language": "ru"},
                    {"id": "Felix-Russian", "name": "Felix", "gender": "male", "language": "ru"},
                    # Dutch
                    {"id": "Ruth-Dutch", "name": "Ruth", "gender": "female", "language": "nl"},
                    {"id": "Daniel-Dutch", "name": "Daniel", "gender": "male", "language": "nl"},
                    # Polish
                    {"id": "Hanna-Polish", "name": "Hanna", "gender": "female", "language": "pl"},
                    {"id": "Pawel - Polish", "name": "Pawel", "gender": "male", "language": "pl"},
                    # Ukrainian
                    {"id": "Vira-Ukrainian", "name": "Vira", "gender": "female", "language": "uk"},
                    {"id": "Dmytro-Ukrainian", "name": "Dmytro", "gender": "male", "language": "uk"},
                    # Swedish
                    {"id": "Sanna-Swedish", "name": "Sanna", "gender": "female", "language": "sv"},
                    {"id": "Adam-Swedish", "name": "Adam", "gender": "male", "language": "sv"},
                ]
            }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


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
    """List all agents for current user (including system agents)"""
    from sqlalchemy import or_
    query = db.query(Agent).filter(
        or_(
            Agent.owner_id == current_user.id,
            Agent.is_system == True  # System agents visible to all
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
    current_user: User = Depends(get_current_user_optional)
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
    
    # Update smart features (Akıllı Özellikler)
    if agent_data.smart_features is not None:
        agent.smart_features = agent_data.smart_features.model_dump() if hasattr(agent_data.smart_features, 'model_dump') else agent_data.smart_features
    
    # Update survey config (Anket Yapılandırması)
    if agent_data.survey_config is not None:
        agent.survey_config = agent_data.survey_config.model_dump() if hasattr(agent_data.survey_config, 'model_dump') else agent_data.survey_config
    
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
    current_user: User = Depends(get_current_user_optional)
):
    """Duplicate an agent with all settings"""
    # System agents can be duplicated by anyone, others only by owner
    original = db.query(Agent).filter(Agent.id == agent_id).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Non-system agents can only be duplicated by owner
    if not original.is_system and original.owner_id != current_user.id:
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
