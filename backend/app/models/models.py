from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    Integer, String, Text, Boolean, DateTime, 
    ForeignKey, Float, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"


class AgentStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CallStatus(str, enum.Enum):
    QUEUED = "queued"
    RINGING = "ringing"
    CONNECTED = "connected"
    TALKING = "talking"
    ON_HOLD = "on_hold"
    TRANSFERRED = "transferred"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"


class CallOutcome(str, enum.Enum):
    SUCCESS = "success"
    VOICEMAIL = "voicemail"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    TRANSFERRED = "transferred"
    CALLBACK_SCHEDULED = "callback_scheduled"


class RealtimeModel(str, enum.Enum):
    """OpenAI Realtime API Model Options"""
    GPT_REALTIME = "gpt-realtime"           # Premium: $32/$64 per 1M tokens
    GPT_REALTIME_MINI = "gpt-realtime-mini"  # Economic: $10/$20 per 1M tokens


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.OPERATOR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agents: Mapped[List["Agent"]] = relationship("Agent", back_populates="owner")
    campaigns: Mapped[List["Campaign"]] = relationship("Campaign", back_populates="owner")


class Agent(Base):
    __tablename__ = "agents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[AgentStatus] = mapped_column(SQLEnum(AgentStatus), default=AgentStatus.DRAFT)
    
    # Model settings
    model_type: Mapped[RealtimeModel] = mapped_column(
        SQLEnum(RealtimeModel), 
        default=RealtimeModel.GPT_REALTIME_MINI  # Default to economic model
    )
    
    # Voice settings
    voice: Mapped[str] = mapped_column(String(50), default="alloy")
    language: Mapped[str] = mapped_column(String(10), default="tr")
    speech_speed: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Greeting settings (First Message)
    first_speaker: Mapped[str] = mapped_column(String(20), default="agent")  # 'agent' or 'user'
    greeting_message: Mapped[Optional[str]] = mapped_column(Text)  # Supports variables: {customer_name}, {company}, etc.
    greeting_uninterruptible: Mapped[bool] = mapped_column(Boolean, default=False)
    first_message_delay: Mapped[float] = mapped_column(Float, default=0.0)  # seconds
    
    # Inactivity messages (JSON array)
    # Format: [{"duration": 30, "message": "Hala orada mısınız?", "end_behavior": "unspecified"}]
    inactivity_messages: Mapped[Optional[str]] = mapped_column(JSON, default=list)
    
    # Knowledge Base / RAG settings
    knowledge_base_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    knowledge_base_ids: Mapped[Optional[str]] = mapped_column(JSON, default=list)  # List of KB IDs
    
    # Prompt sections
    prompt_role: Mapped[Optional[str]] = mapped_column(Text)
    prompt_personality: Mapped[Optional[str]] = mapped_column(Text)
    prompt_language: Mapped[Optional[str]] = mapped_column(Text)
    prompt_flow: Mapped[Optional[str]] = mapped_column(Text)
    prompt_tools: Mapped[Optional[str]] = mapped_column(Text)
    prompt_safety: Mapped[Optional[str]] = mapped_column(Text)
    prompt_rules: Mapped[Optional[str]] = mapped_column(Text)
    
    # Call settings
    max_duration: Mapped[int] = mapped_column(Integer, default=300)
    silence_timeout: Mapped[int] = mapped_column(Integer, default=10)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay: Mapped[int] = mapped_column(Integer, default=60)
    
    # Behavior settings
    interruptible: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_transcribe: Mapped[bool] = mapped_column(Boolean, default=True)
    record_calls: Mapped[bool] = mapped_column(Boolean, default=True)
    human_transfer: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Advanced settings
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    vad_threshold: Mapped[float] = mapped_column(Float, default=0.5)
    turn_detection: Mapped[str] = mapped_column(String(50), default="server_vad")
    
    # Statistics
    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    successful_calls: Mapped[int] = mapped_column(Integer, default=0)
    avg_duration: Mapped[float] = mapped_column(Float, default=0)
    
    # Metadata
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="agents")
    campaigns: Mapped[List["Campaign"]] = relationship("Campaign", back_populates="agent")
    call_logs: Mapped[List["CallLog"]] = relationship("CallLog", back_populates="agent")


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Template content
    role: Mapped[Optional[str]] = mapped_column(Text)
    personality: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(Text)
    flow: Mapped[Optional[str]] = mapped_column(Text)
    tools: Mapped[Optional[str]] = mapped_column(Text)
    safety: Mapped[Optional[str]] = mapped_column(Text)
    rules: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float] = mapped_column(Float, default=0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NumberList(Base):
    __tablename__ = "number_lists"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    total_numbers: Mapped[int] = mapped_column(Integer, default=0)
    valid_numbers: Mapped[int] = mapped_column(Integer, default=0)
    invalid_numbers: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="processing")  # processing, ready, error
    
    # Custom fields mapping
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON)  # Store field mappings
    
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    phone_numbers: Mapped[List["PhoneNumber"]] = relationship("PhoneNumber", back_populates="number_list")


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Custom data from Excel
    custom_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Call tracking
    call_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_call_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_outcome: Mapped[Optional[CallOutcome]] = mapped_column(SQLEnum(CallOutcome))
    
    number_list_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("number_lists.id"))
    
    # Relationships
    number_list: Mapped[Optional["NumberList"]] = relationship("NumberList", back_populates="phone_numbers")
    call_logs: Mapped[List["CallLog"]] = relationship("CallLog", back_populates="phone_number")


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[CampaignStatus] = mapped_column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT)
    
    # Schedule
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    call_hours_start: Mapped[str] = mapped_column(String(10), default="09:00")
    call_hours_end: Mapped[str] = mapped_column(String(10), default="20:00")
    active_days: Mapped[Optional[list]] = mapped_column(JSON, default=[1, 2, 3, 4, 5])  # 1=Monday, 7=Sunday
    
    # Statistics
    total_numbers: Mapped[int] = mapped_column(Integer, default=0)
    completed_calls: Mapped[int] = mapped_column(Integer, default=0)
    successful_calls: Mapped[int] = mapped_column(Integer, default=0)
    failed_calls: Mapped[int] = mapped_column(Integer, default=0)
    active_calls: Mapped[int] = mapped_column(Integer, default=0)
    
    # Configuration
    concurrent_calls: Mapped[int] = mapped_column(Integer, default=10)
    retry_strategy: Mapped[Optional[dict]] = mapped_column(JSON)  # Retry configuration
    
    # Relationships
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id"))
    number_list_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("number_lists.id"))
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    
    agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="campaigns")
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="campaigns")
    call_logs: Mapped[List["CallLog"]] = relationship("CallLog", back_populates="campaign")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CallLog(Base):
    __tablename__ = "call_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    call_sid: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    # Call details
    status: Mapped[CallStatus] = mapped_column(SQLEnum(CallStatus), default=CallStatus.QUEUED)
    outcome: Mapped[Optional[CallOutcome]] = mapped_column(SQLEnum(CallOutcome))
    duration: Mapped[int] = mapped_column(Integer, default=0)  # seconds
    
    # Parties
    from_number: Mapped[Optional[str]] = mapped_column(String(50))
    to_number: Mapped[Optional[str]] = mapped_column(String(50))
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Recording
    recording_url: Mapped[Optional[str]] = mapped_column(String(500))
    recording_duration: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Transcription
    transcription: Mapped[Optional[str]] = mapped_column(Text)
    transcription_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Analysis
    sentiment: Mapped[Optional[str]] = mapped_column(String(50))  # positive, neutral, negative
    intent: Mapped[Optional[str]] = mapped_column(String(100))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    
    # Outcomes
    payment_promise_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    payment_promise_amount: Mapped[Optional[float]] = mapped_column(Float)
    callback_scheduled: Mapped[Optional[datetime]] = mapped_column(DateTime)
    transfer_reason: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Token usage & cost tracking
    model_used: Mapped[Optional[str]] = mapped_column(String(50))  # gpt-realtime or gpt-realtime-mini
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)  # USD
    
    # Custom notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    call_metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # renamed from metadata
    
    # Relationships
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("campaigns.id"))
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id"))
    phone_number_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("phone_numbers.id"))
    
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="call_logs")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="call_logs")
    phone_number: Mapped[Optional["PhoneNumber"]] = relationship("PhoneNumber", back_populates="call_logs")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SIPTrunk(Base):
    __tablename__ = "sip_trunks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Connection settings
    server: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=5060)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    password: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Configuration
    transport: Mapped[str] = mapped_column(String(10), default="udp")  # udp, tcp, tls
    codec_priority: Mapped[str] = mapped_column(String(50), default="opus")
    concurrent_limit: Mapped[int] = mapped_column(Integer, default=50)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Metadata
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    events: Mapped[Optional[list]] = mapped_column(JSON)  # List of subscribed events
    secret: Mapped[Optional[str]] = mapped_column(String(255))  # For signature verification
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Statistics
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    failed_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    last_delivery_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class APIKey(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    key_prefix: Mapped[Optional[str]] = mapped_column(String(20))  # First few chars for identification
    
    # Permissions
    scopes: Mapped[Optional[list]] = mapped_column(JSON)  # List of allowed scopes
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeBase(Base):
    """Knowledge Base for RAG (Retrieval Augmented Generation)"""
    __tablename__ = "knowledge_bases"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="processing")  # processing, ready, error
    
    # Vector DB settings
    vector_store_id: Mapped[Optional[str]] = mapped_column(String(255))  # External vector store ID
    embedding_model: Mapped[str] = mapped_column(String(100), default="text-embedding-3-small")
    chunk_size: Mapped[int] = mapped_column(Integer, default=1000)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200)
    
    # Statistics
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents: Mapped[List["KnowledgeDocument"]] = relationship("KnowledgeDocument", back_populates="knowledge_base")


class KnowledgeDocument(Base):
    """Documents in Knowledge Base"""
    __tablename__ = "knowledge_documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))  # pdf, txt, docx, csv, etc.
    file_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Processing status
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, ready, error
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Stats
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    knowledge_base_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_bases.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
