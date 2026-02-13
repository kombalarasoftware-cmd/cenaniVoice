from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    Integer, String, Text, Boolean, DateTime,
    ForeignKey, Float, JSON, Enum as SQLEnum,
    Index, UniqueConstraint, func
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


class AppointmentStatus(str, enum.Enum):
    """Appointment confirmation status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class AppointmentType(str, enum.Enum):
    """Types of appointments"""
    CONSULTATION = "consultation"  # Consultation
    SITE_VISIT = "site_visit"      # Site visit
    INSTALLATION = "installation"  # Installation
    MAINTENANCE = "maintenance"    # Maintenance
    DEMO = "demo"                  # Demo/Presentation
    OTHER = "other"


class LeadStatus(str, enum.Enum):
    """Lead/Prospect status"""
    NEW = "new"                    # Newly captured
    CONTACTED = "contacted"        # Contacted
    QUALIFIED = "qualified"        # Qualified lead
    CONVERTED = "converted"        # Converted to customer
    LOST = "lost"                  # Lost


class LeadInterestType(str, enum.Enum):
    """Type of interest shown by lead"""
    CALLBACK = "callback"                    # Requested callback
    ADDRESS_COLLECTION = "address_collection"  # Shared address info
    PURCHASE_INTENT = "purchase_intent"      # Purchase intent
    DEMO_REQUEST = "demo_request"            # Requested demo
    QUOTE_REQUEST = "quote_request"          # Requested quote
    SUBSCRIPTION = "subscription"            # Subscription interest
    INFORMATION = "information"              # Requested info
    OTHER = "other"


class CallTag(str, enum.Enum):
    """Tags for call categorization"""
    INTERESTED = "interested"              # Interested
    NOT_INTERESTED = "not_interested"      # Not interested
    CALLBACK_REQUESTED = "callback"        # Requested callback
    HOT_LEAD = "hot_lead"                  # Hot lead
    COLD_LEAD = "cold_lead"                # Cold lead
    DO_NOT_CALL = "do_not_call"            # Do not call
    WRONG_NUMBER = "wrong_number"          # Wrong number
    VOICEMAIL = "voicemail"                # Voicemail
    BUSY = "busy"                          # Busy
    COMPLAINT = "complaint"                # Complaint


class SurveyQuestionType(str, enum.Enum):
    """Types of survey questions"""
    YES_NO = "yes_no"                      # Yes/No question
    MULTIPLE_CHOICE = "multiple_choice"    # Multiple choice (A, B, C, D)
    RATING = "rating"                      # Rating/Score (1-5 or 1-10)
    OPEN_ENDED = "open_ended"              # Open-ended (free text)


class SurveyStatus(str, enum.Enum):
    """Survey completion status"""
    NOT_STARTED = "not_started"            # Not started
    IN_PROGRESS = "in_progress"            # In progress
    COMPLETED = "completed"                # Completed
    ABANDONED = "abandoned"                # Abandoned


class AIProvider(str, enum.Enum):
    """AI voice call provider"""
    OPENAI = "openai"
    ULTRAVOX = "ultravox"
    XAI = "xai"
    GEMINI = "gemini"


class RealtimeModel(str, enum.Enum):
    """AI Model Options (OpenAI, Ultravox, xAI, and Gemini)"""
    # OpenAI models
    GPT_REALTIME = "gpt-realtime"           # Premium: $32/$64 per 1M tokens
    GPT_REALTIME_MINI = "gpt-realtime-mini"  # Economic: $10/$20 per 1M tokens
    # Ultravox models (current default: ultravox-v0.7)
    ULTRAVOX = "ultravox-v0.7"  # Ultravox latest (default)
    ULTRAVOX_V0_6 = "ultravox-v0.6"
    ULTRAVOX_V0_6_GEMMA3_27B = "ultravox-v0.6-gemma3-27b"
    ULTRAVOX_V0_6_LLAMA3_3_70B = "ultravox-v0.6-llama3.3-70b"
    # xAI Grok models
    XAI_GROK = "grok-2-realtime"                 # xAI Grok voice, per-minute billing
    # Google Gemini Live models (Vertex AI)
    GEMINI_LIVE = "gemini-live-2.5-flash-native-audio"  # GA model
    GEMINI_LIVE_PREVIEW = "gemini-live-2.5-flash-preview-native-audio-09-2025"  # Preview


class TranscriptModel(str, enum.Enum):
    """User Transcript Model for speech-to-text"""
    GPT_4O_TRANSCRIBE = "gpt-4o-transcribe"  # Newer, more accurate, higher latency
    WHISPER_1 = "whisper-1"  # Lower latency, good accuracy


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.OPERATOR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
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
    
    # Provider selection
    provider: Mapped[str] = mapped_column(String(20), default="openai")  # "openai", "ultravox", or "xai"

    # Model settings
    model_type: Mapped[RealtimeModel] = mapped_column(
        SQLEnum(RealtimeModel),
        default=RealtimeModel.GPT_REALTIME_MINI  # Default to economic model
    )

    # Ultravox-specific
    ultravox_agent_id: Mapped[Optional[str]] = mapped_column(String(255))  # Ultravox-side agent ID

    # Voice settings
    voice: Mapped[str] = mapped_column(String(50), default="alloy")
    language: Mapped[str] = mapped_column(String(10), default="tr")
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Istanbul")
    speech_speed: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Greeting settings (First Message)
    first_speaker: Mapped[str] = mapped_column(String(20), default="agent")  # 'agent' or 'user'
    greeting_message: Mapped[Optional[str]] = mapped_column(Text)  # Supports variables: {customer_name}, {company}, etc.
    greeting_uninterruptible: Mapped[bool] = mapped_column(Boolean, default=False)
    first_message_delay: Mapped[float] = mapped_column(Float, default=0.0)  # seconds
    
    # Inactivity messages (JSON array)
    # Format: [{"duration": 30, "message": "Are you still there?", "end_behavior": "unspecified"}]
    inactivity_messages: Mapped[Optional[str]] = mapped_column(JSON, default=list)
    
    # Knowledge Base / RAG settings
    knowledge_base_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    knowledge_base_ids: Mapped[Optional[str]] = mapped_column(JSON, default=list)  # List of KB IDs
    knowledge_base: Mapped[Optional[str]] = mapped_column(Text)  # Static knowledge base content (embedded in prompt)
    web_sources: Mapped[Optional[str]] = mapped_column(JSON, default=list)  # Web URLs for dynamic info retrieval
    
    # Prompt sections (10-section standard structure)
    # 1. Personality - who the agent is, character traits
    prompt_role: Mapped[Optional[str]] = mapped_column(Text)  # DB column kept as prompt_role for compat
    # 2. Environment - context of the conversation
    prompt_personality: Mapped[Optional[str]] = mapped_column(Text)  # DB column kept as prompt_personality for compat
    # 3. Tone - how to speak (concise, clear, professional)
    prompt_context: Mapped[Optional[str]] = mapped_column(Text)  # DB column kept as prompt_context for compat
    # 4. Goal - what to accomplish, numbered workflow steps
    prompt_pronunciations: Mapped[Optional[str]] = mapped_column(Text)  # DB column kept for compat
    # 5. Guardrails - non-negotiable rules (models pay extra attention to this heading)
    prompt_sample_phrases: Mapped[Optional[str]] = mapped_column(Text)  # DB column kept for compat
    # 6. Tools - tool descriptions with when/how/error handling
    prompt_tools: Mapped[Optional[str]] = mapped_column(Text)
    # 7. Character normalization - spoken vs written format rules
    prompt_rules: Mapped[Optional[str]] = mapped_column(Text)  # DB column kept as prompt_rules for compat
    # 8. Error handling - tool failure recovery instructions
    prompt_flow: Mapped[Optional[str]] = mapped_column(Text)  # DB column kept as prompt_flow for compat
    # 9. Safety & Escalation - fallback and handoff logic (legacy, merged into guardrails)
    prompt_safety: Mapped[Optional[str]] = mapped_column(Text)
    # Legacy field
    prompt_language: Mapped[Optional[str]] = mapped_column(Text)
    
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
    vad_threshold: Mapped[float] = mapped_column(Float, default=0.3)  # Lower = more sensitive (0.0-1.0)
    turn_detection: Mapped[str] = mapped_column(String(50), default="server_vad")  # server_vad, semantic_vad, disabled
    vad_eagerness: Mapped[str] = mapped_column(String(20), default="auto")  # semantic_vad: low, medium, high, auto
    silence_duration_ms: Mapped[int] = mapped_column(Integer, default=800)  # server_vad silence detection (ms)
    prefix_padding_ms: Mapped[int] = mapped_column(Integer, default=500)  # server_vad prefix padding (ms)
    idle_timeout_ms: Mapped[Optional[int]] = mapped_column(Integer, default=None)  # VAD idle timeout (ms), None = no timeout
    interrupt_response: Mapped[bool] = mapped_column(Boolean, default=True)  # Allow user to interrupt model
    create_response: Mapped[bool] = mapped_column(Boolean, default=True)  # Auto create response on speech end
    noise_reduction: Mapped[bool] = mapped_column(Boolean, default=True)  # Input audio noise reduction
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=500)  # Max response tokens (0=infinite)
    
    # Transcript settings
    transcript_model: Mapped[str] = mapped_column(String(50), default="gpt-4o-transcribe")  # gpt-4o-transcribe, whisper-1
    
    # Statistics
    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    successful_calls: Mapped[int] = mapped_column(Integer, default=0)
    avg_duration: Mapped[float] = mapped_column(Float, default=0)
    
    # System flag (cannot be deleted)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Smart Features
    # JSON structure for lead capture, call tags, callback scheduling settings
    # Example: {
    #   "lead_capture": {"enabled": true, "triggers": ["interested", "callback"], "default_priority": 2},
    #   "call_tags": {"enabled": true, "auto_tags": ["interested", "callback"]},
    #   "callback": {"enabled": true, "default_delay_hours": 24}
    # }
    smart_features: Mapped[Optional[str]] = mapped_column(JSON, default=dict)
    
    # Survey Configuration
    # JSON structure for survey questions with conditional branching
    # Example: {
    #   "enabled": true,
    #   "questions": [
    #     {"id": "q1", "type": "yes_no", "text": "Are you satisfied?", "next_on_yes": "q2a", "next_on_no": "q2b"},
    #     {"id": "q2a", "type": "rating", "text": "Would you rate us 1-10?", "min": 1, "max": 10, "next": null},
    #     {"id": "q2b", "type": "multiple_choice", "text": "What should we improve?", "options": ["Speed", "Price", "Quality"], "next": null}
    #   ],
    #   "start_question": "q1",
    #   "completion_message": "Thank you for participating in our survey!"
    # }
    survey_config: Mapped[Optional[str]] = mapped_column(JSON, default=dict)
    
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
    
    # Template content (10-section standard structure)
    role: Mapped[Optional[str]] = mapped_column(Text)  # Role
    personality: Mapped[Optional[str]] = mapped_column(Text)  # Environment
    context: Mapped[Optional[str]] = mapped_column(Text)  # Tone
    pronunciations: Mapped[Optional[str]] = mapped_column(Text)  # Goal
    sample_phrases: Mapped[Optional[str]] = mapped_column(Text)  # Guardrails
    tools: Mapped[Optional[str]] = mapped_column(Text)  # Tools
    rules: Mapped[Optional[str]] = mapped_column(Text)  # Instructions
    flow: Mapped[Optional[str]] = mapped_column(Text)  # Conversation Flow
    safety: Mapped[Optional[str]] = mapped_column(Text)  # Safety & Escalation
    language: Mapped[Optional[str]] = mapped_column(Text)  # Language
    
    # Metadata
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float] = mapped_column(Float, default=0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptHistory(Base):
    """Stores generated prompts from the Prompt Maker feature"""
    __tablename__ = "prompt_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, ultravox, xai, gemini
    agent_type: Mapped[Optional[str]] = mapped_column(String(50))  # sales, support, collection, appointment, survey
    tone: Mapped[Optional[str]] = mapped_column(String(50))  # professional, friendly, formal, casual
    language: Mapped[str] = mapped_column(String(10), default="en")
    description: Mapped[Optional[str]] = mapped_column(Text)  # User's original description
    generated_prompt: Mapped[str] = mapped_column(Text, nullable=False)  # The full generated prompt
    applied_to_agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id", ondelete="SET NULL"))
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    owner: Mapped["User"] = relationship("User")
    applied_to_agent: Mapped[Optional["Agent"]] = relationship("Agent")


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
    timezone: Mapped[Optional[str]] = mapped_column(String(50))  # e.g., "Europe/Istanbul"

    # Custom data from Excel
    custom_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # Call tracking
    call_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_call_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_outcome: Mapped[Optional[CallOutcome]] = mapped_column(SQLEnum(CallOutcome))

    number_list_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("number_lists.id"))
    lead_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("leads.id"), nullable=True)

    # Relationships
    number_list: Mapped[Optional["NumberList"]] = relationship("NumberList", back_populates="phone_numbers")
    call_logs: Mapped[List["CallLog"]] = relationship("CallLog", back_populates="phone_number")
    lead: Mapped[Optional["Lead"]] = relationship("Lead", backref="phone_numbers")


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
    dialing_mode: Mapped[str] = mapped_column(String(20), default="power")  # progressive, power, preview

    # Ultravox batch tracking
    ultravox_batch_id: Mapped[Optional[str]] = mapped_column(String(255))

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

    # Provider tracking
    provider: Mapped[Optional[str]] = mapped_column(String(20))  # "openai" or "ultravox"
    ultravox_call_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)  # Ultravox call UUID

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

    # SIP/Hangup details
    sip_code: Mapped[Optional[int]] = mapped_column(Integer)  # SIP response code (200, 403, 486, 503, etc.)
    hangup_cause: Mapped[Optional[str]] = mapped_column(String(100))  # Asterisk hangup cause text

    # AMD (Answering Machine Detection)
    amd_status: Mapped[Optional[str]] = mapped_column(String(20))  # HUMAN, MACHINE, NOTSURE
    amd_cause: Mapped[Optional[str]] = mapped_column(String(100))  # AMD decision reason

    # Token usage & cost tracking
    model_used: Mapped[Optional[str]] = mapped_column(String(50))  # gpt-realtime or gpt-realtime-mini
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)  # USD
    
    # Custom notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    call_metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # renamed from metadata
    
    # Tags for categorization (JSON array of strings)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # ["interested", "hot_lead", etc.]
    
    # ViciDial dialing link
    dial_attempt_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("dial_attempts.id"), nullable=True)

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


class RolePermission(Base):
    """Role-based page access permissions"""
    __tablename__ = "role_permissions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)


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


class AgentDocument(Base):
    """Documents uploaded directly to an Agent for RAG search"""
    __tablename__ = "agent_documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    
    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))  # pdf, txt, docx
    file_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes
    file_path: Mapped[Optional[str]] = mapped_column(String(500))  # MinIO path
    
    # Processing status
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, ready, error
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Stats
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", backref="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Chunks with embeddings for semantic search"""
    __tablename__ = "document_chunks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_documents.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), index=True)  # Denormalized for fast lookup
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)  # Order in document
    
    # Token count for this chunk
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document: Mapped["AgentDocument"] = relationship("AgentDocument", back_populates="chunks")
    
    # Note: embedding column is added via migration as vector(1536) type
    # SQLAlchemy doesn't have native pgvector support, we use raw SQL for vector operations


class Appointment(Base):
    """Appointments confirmed during AI calls"""
    __tablename__ = "appointments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Relationship to call and agent
    call_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("call_logs.id"), index=True)
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("campaigns.id"), index=True)
    
    # Customer info (from call or campaign contact)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    customer_phone: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))
    customer_address: Mapped[Optional[str]] = mapped_column(Text)
    
    # Appointment details
    appointment_type: Mapped[AppointmentType] = mapped_column(
        SQLEnum(AppointmentType), 
        default=AppointmentType.CONSULTATION
    )
    appointment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    appointment_time: Mapped[Optional[str]] = mapped_column(String(20))  # e.g., "14:00", "09:00-10:00"
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    
    # Status
    status: Mapped[AppointmentStatus] = mapped_column(
        SQLEnum(AppointmentStatus),
        default=AppointmentStatus.CONFIRMED
    )
    
    # Additional info
    notes: Mapped[Optional[str]] = mapped_column(Text)  # AI summary or customer notes
    location: Mapped[Optional[str]] = mapped_column(String(500))  # Visit address if different
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # When customer confirmed
    
    # Relationships
    call: Mapped[Optional["CallLog"]] = relationship("CallLog", backref="appointments")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", backref="appointments")
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", backref="appointments")


class Lead(Base):
    """Leads/Prospects captured during AI calls"""
    __tablename__ = "leads"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Relationship to call and agent
    call_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("call_logs.id"), index=True)
    agent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agents.id"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("campaigns.id"), index=True)
    
    # Customer info
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    customer_phone: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))
    customer_address: Mapped[Optional[str]] = mapped_column(Text)
    
    # Lead details
    interest_type: Mapped[LeadInterestType] = mapped_column(
        SQLEnum(LeadInterestType), 
        default=LeadInterestType.CALLBACK
    )
    status: Mapped[LeadStatus] = mapped_column(
        SQLEnum(LeadStatus),
        default=LeadStatus.NEW
    )
    
    # Customer's exact words (what they said to trigger capture)
    customer_statement: Mapped[Optional[str]] = mapped_column(Text)
    
    # Additional info
    notes: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1=low, 2=medium, 3=high
    source: Mapped[Optional[str]] = mapped_column(String(100))  # campaign name, inbound, etc.
    
    # Follow-up tracking
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_follow_up: Mapped[Optional[datetime]] = mapped_column(DateTime)
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # When lead became customer
    
    # Relationships
    call: Mapped[Optional["CallLog"]] = relationship("CallLog", backref="leads")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", backref="leads")
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", backref="leads")


class SurveyResponse(Base):
    """Survey responses collected during AI calls"""
    __tablename__ = "survey_responses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Relationship to call and agent
    call_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("call_logs.id"), index=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("campaigns.id"), index=True)
    
    # Respondent info
    respondent_phone: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    respondent_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Survey status
    status: Mapped[SurveyStatus] = mapped_column(
        SQLEnum(SurveyStatus),
        default=SurveyStatus.NOT_STARTED
    )
    
    # Answers stored as JSON
    # Format: [{"question_id": "q1", "question_text": "...", "answer": "...", "answer_value": 5}]
    answers: Mapped[Optional[str]] = mapped_column(JSON, default=list)
    
    # Progress tracking
    current_question_id: Mapped[Optional[str]] = mapped_column(String(50))
    questions_answered: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    
    # Completion metrics
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)  # Time to complete
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    call: Mapped[Optional["CallLog"]] = relationship("CallLog", backref="survey_responses")
    agent: Mapped["Agent"] = relationship("Agent", backref="survey_responses")
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", backref="survey_responses")


# ============================================
# ViciDial-Style Dialing Models
# ============================================

class DialListStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class DialEntryStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    DNC = "dnc"
    CALLBACK = "callback"
    COMPLETED = "completed"
    INVALID = "invalid"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    FAILED = "failed"


class DialAttemptResult(str, enum.Enum):
    CONNECTED = "connected"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    VOICEMAIL = "voicemail"
    DNC = "dnc"
    INVALID_NUMBER = "invalid_number"
    CONGESTION = "congestion"
    TIMEOUT = "timeout"


class DialingMode(str, enum.Enum):
    PROGRESSIVE = "progressive"
    POWER = "power"
    PREVIEW = "preview"


class DialList(Base):
    __tablename__ = "dial_lists"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String(255), nullable=False)
    description = mapped_column(Text)
    status = mapped_column(String(20), default=DialListStatus.ACTIVE)
    total_numbers = mapped_column(Integer, default=0)
    active_numbers = mapped_column(Integer, default=0)
    completed_numbers = mapped_column(Integer, default=0)
    invalid_numbers = mapped_column(Integer, default=0)
    owner_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", backref="dial_lists")
    entries = relationship("DialListEntry", back_populates="dial_list", cascade="all, delete-orphan")
    campaign_lists = relationship("CampaignList", back_populates="dial_list")


class DialListEntry(Base):
    __tablename__ = "dial_list_entries"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    list_id = mapped_column(Integer, ForeignKey("dial_lists.id", ondelete="CASCADE"), nullable=False)
    phone_number = mapped_column(String(20), nullable=False, index=True)
    first_name = mapped_column(String(100))
    last_name = mapped_column(String(100))
    email = mapped_column(String(255))
    company = mapped_column(String(255))
    timezone = mapped_column(String(50))  # e.g., "Europe/Istanbul"
    priority = mapped_column(Integer, default=0)
    status = mapped_column(String(20), default=DialEntryStatus.NEW)
    call_attempts = mapped_column(Integer, default=0)
    max_attempts = mapped_column(Integer, default=3)
    last_attempt_at = mapped_column(DateTime(timezone=True))
    next_callback_at = mapped_column(DateTime(timezone=True))
    dnc_flag = mapped_column(Boolean, default=False)
    custom_fields = mapped_column(JSON, default=dict)
    notes = mapped_column(Text)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    dial_list = relationship("DialList", back_populates="entries")
    dial_attempts = relationship("DialAttempt", back_populates="entry", cascade="all, delete-orphan")

    # Composite indexes for efficient querying
    __table_args__ = (
        Index('idx_entry_list_status', 'list_id', 'status'),
        Index('idx_entry_phone', 'phone_number'),
        Index('idx_entry_callback', 'next_callback_at'),
    )


class DialAttempt(Base):
    __tablename__ = "dial_attempts"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id = mapped_column(Integer, ForeignKey("dial_list_entries.id", ondelete="CASCADE"), nullable=False)
    campaign_id = mapped_column(Integer, ForeignKey("campaigns.id"), nullable=False)
    call_log_id = mapped_column(Integer, ForeignKey("call_logs.id"))
    attempt_number = mapped_column(Integer, nullable=False)
    result = mapped_column(String(20), nullable=False)
    sip_code = mapped_column(Integer)
    hangup_cause = mapped_column(String(100))
    duration = mapped_column(Integer, default=0)  # seconds
    started_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at = mapped_column(DateTime(timezone=True))

    # Relationships
    entry = relationship("DialListEntry", back_populates="dial_attempts")
    campaign = relationship("Campaign")
    call_log = relationship("CallLog", foreign_keys="[DialAttempt.call_log_id]")

    __table_args__ = (
        Index('idx_attempt_campaign', 'campaign_id', 'result'),
        Index('idx_attempt_entry', 'entry_id', 'attempt_number'),
    )


class DNCList(Base):
    __tablename__ = "dnc_list"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone_number = mapped_column(String(20), nullable=False, unique=True, index=True)
    source = mapped_column(String(50))  # "manual", "customer_request", "regulatory", "import"
    reason = mapped_column(Text)
    added_by = mapped_column(Integer, ForeignKey("users.id"))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")


class CampaignList(Base):
    __tablename__ = "campaign_lists"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id = mapped_column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    list_id = mapped_column(Integer, ForeignKey("dial_lists.id", ondelete="CASCADE"), nullable=False)
    priority = mapped_column(Integer, default=0)  # Higher = dialed first
    active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", backref="campaign_lists")
    dial_list = relationship("DialList", back_populates="campaign_lists")

    __table_args__ = (
        UniqueConstraint('campaign_id', 'list_id', name='uq_campaign_list'),
    )


class DialHopper(Base):
    __tablename__ = "dial_hopper"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id = mapped_column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_id = mapped_column(Integer, ForeignKey("dial_list_entries.id", ondelete="CASCADE"), nullable=False)
    priority = mapped_column(Integer, default=0)
    status = mapped_column(String(20), default="waiting")  # waiting, dialing, done
    inserted_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign")
    entry = relationship("DialListEntry")

    __table_args__ = (
        Index('idx_hopper_campaign_status', 'campaign_id', 'status', 'priority'),
    )


class CampaignDisposition(Base):
    __tablename__ = "campaign_dispositions"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id = mapped_column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    name = mapped_column(String(100), nullable=False)
    category = mapped_column(String(50))  # "success", "failure", "retry", "dnc"
    next_action = mapped_column(String(50))  # "none", "retry", "callback", "dnc", "transfer"
    retry_delay_minutes = mapped_column(Integer, default=60)
    is_final = mapped_column(Boolean, default=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", backref="dispositions")
