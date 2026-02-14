"""
Pydantic schemas for request/response validation.
Enums are imported from models to maintain single source of truth.
"""

import enum
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

# Import enums from models - Single Source of Truth
from app.models.models import (
    UserRole,
    AgentStatus,
    CampaignStatus,
    CallStatus,
    CallOutcome,
    RealtimeModel,
    TranscriptModel,
    AppointmentStatus,
    AppointmentType,
    LeadStatus,
    LeadInterestType,
    CallTag,
    AIProvider,
    DialListStatus,
    DialEntryStatus,
    DialAttemptResult,
    DialingMode,
)


# ============ User Schemas ============

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Auth Schemas ============

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ============ Agent Schemas ============

class PromptSections(BaseModel):
    """
    Structured prompt sections following OpenAI Realtime Prompting Guide.
    See: https://cookbook.openai.com/examples/realtime_prompting_guide
    """
    # 1. Role & Objective - who you are and what "success" means
    role: Optional[str] = Field(default=None, description="Role definition and main objective")
    # 2. Personality & Tone - voice, style, pacing, length, variety
    personality: Optional[str] = Field(default=None, description="Personality, tone, pacing, response length")
    # 3. Context - additional info for RAG/KB (optional)
    context: Optional[str] = Field(default=None, description="Additional context, retrieved info")
    # 4. Reference Pronunciations - phonetic guides for names/terms
    pronunciations: Optional[str] = Field(default=None, description="Phonetic guides for brand names, technical terms")
    # 5. Sample Phrases - anchor examples for style consistency
    sample_phrases: Optional[str] = Field(default=None, description="Sample phrases for style, brevity, tone")
    # 6. Tools - function descriptions, usage rules
    tools: Optional[str] = Field(default=None, description="Tool usage rules, preambles")
    # 7. Instructions/Rules - do's, don'ts, approach
    rules: Optional[str] = Field(default=None, description="Instructions, rules, guidelines")
    # 8. Conversation Flow - states, goals, transitions
    flow: Optional[str] = Field(default=None, description="Conversation states, goals, exit criteria")
    # 9. Safety & Escalation - fallback and handoff logic
    safety: Optional[str] = Field(default=None, description="Safety rules, escalation triggers")
    # 10. Language - language and register guidelines
    language: Optional[str] = Field(default=None, description="Language and register guidelines for the conversation")


class VoiceSettings(BaseModel):
    model_type: RealtimeModel = RealtimeModel.GPT_REALTIME_MINI  # Default to economic
    voice: str = "alloy"
    language: str = "tr"
    timezone: str = "Europe/Istanbul"
    speech_speed: float = Field(default=1.0, ge=0.5, le=2.0)


class CallSettings(BaseModel):
    max_duration: int = Field(default=300, ge=60, le=600)
    silence_timeout: int = Field(default=10, ge=5, le=30)
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay: int = Field(default=60, ge=30, le=1440)


class BehaviorSettings(BaseModel):
    interruptible: bool = True
    auto_transcribe: bool = True
    record_calls: bool = True
    human_transfer: bool = True


class AdvancedSettings(BaseModel):
    temperature: float = Field(default=0.7, ge=0, le=1)
    vad_threshold: float = Field(default=0.5, ge=0, le=1)  # Balanced sensitivity (0.0-1.0)
    turn_detection: str = "semantic_vad"  # server_vad, semantic_vad, disabled
    vad_eagerness: str = "low"  # semantic_vad: low, medium, high, auto
    silence_duration_ms: int = Field(default=1000, ge=100, le=5000)  # server_vad silence duration (ms)
    prefix_padding_ms: int = Field(default=400, ge=100, le=2000)  # server_vad prefix padding (ms)
    idle_timeout_ms: Optional[int] = Field(default=None, ge=0, le=60000)  # VAD idle timeout, None=no timeout
    interrupt_response: bool = True  # Stop AI when user speaks
    create_response: bool = True  # Auto-respond when user stops
    noise_reduction: bool = True
    max_output_tokens: int = Field(default=500, ge=0, le=4096)  # 0=infinite
    transcript_model: str = "gpt-4o-transcribe"  # gpt-4o-transcribe, whisper-1


class GreetingSettings(BaseModel):
    first_speaker: str = "agent"  # 'agent' or 'user'
    greeting_message: Optional[str] = None
    greeting_uninterruptible: bool = False
    first_message_delay: float = 0.0


class InactivityMessage(BaseModel):
    duration: int = 30
    message: str = ""
    end_behavior: str = "unspecified"  # 'unspecified', 'interruptible_hangup', 'uninterruptible_hangup'


# ============ Smart Features ============

class LeadCaptureTrigger(str, enum.Enum):
    """Triggers for automatic lead capture"""
    INTERESTED = "interested"  # Customer showed interest
    CALLBACK = "callback"  # Wants to be called back
    PURCHASE = "purchase"  # Purchase intent
    SUBSCRIPTION = "subscription"  # Subscription/membership
    INFO_REQUEST = "info_request"  # Information request
    ADDRESS_SHARED = "address_shared"  # Shared address


class LeadCaptureSettings(BaseModel):
    """Lead capture settings"""
    enabled: bool = False
    triggers: List[LeadCaptureTrigger] = Field(default_factory=list)
    default_priority: int = Field(default=2, ge=1, le=3)  # 1=high, 2=medium, 3=low
    auto_capture_phone: bool = True  # Automatically capture phone number
    auto_capture_address: bool = False  # Automatically capture address
    require_confirmation: bool = True  # Ask customer for confirmation


class CallTagSettings(BaseModel):
    """Call tagging settings"""
    enabled: bool = False
    auto_tags: List[str] = Field(default_factory=list)  # Tags to add automatically
    tag_on_interest: bool = True  # Tag when interest shown
    tag_on_rejection: bool = True  # Tag when rejected
    tag_on_callback: bool = True  # Tag when callback requested


class CallbackSettings(BaseModel):
    """Callback scheduling settings"""
    enabled: bool = False
    default_delay_hours: int = Field(default=24, ge=1, le=168)  # Default callback delay (hours)
    max_attempts: int = Field(default=3, ge=1, le=10)  # Maximum retry attempts
    respect_business_hours: bool = True  # Respect business hours
    ask_preferred_time: bool = True  # Ask customer for preferred time


class SmartFeatures(BaseModel):
    """Smart features - all settings"""
    lead_capture: Optional[LeadCaptureSettings] = None
    call_tags: Optional[CallTagSettings] = None
    callback: Optional[CallbackSettings] = None


# ==================== SURVEY SCHEMAS ====================

class SurveyQuestionType(str, enum.Enum):
    """Survey question types"""
    YES_NO = "yes_no"  # Yes/No
    MULTIPLE_CHOICE = "multiple_choice"  # Multiple choice
    RATING = "rating"  # 1-10 rating
    OPEN_ENDED = "open_ended"  # Open-ended


class SurveyQuestionBase(BaseModel):
    """Survey question base structure"""
    id: str = Field(..., description="Unique question ID (e.g.: q1, q2a)")
    type: SurveyQuestionType
    text: str = Field(..., description="Question text")
    required: bool = True


class SurveyQuestionYesNo(SurveyQuestionBase):
    """Yes/No question - with conditional branching support"""
    type: SurveyQuestionType = SurveyQuestionType.YES_NO
    next_on_yes: Optional[str] = Field(None, description="Next question ID on Yes answer")
    next_on_no: Optional[str] = Field(None, description="Next question ID on No answer")


class SurveyQuestionMultipleChoice(SurveyQuestionBase):
    """Multiple choice question"""
    type: SurveyQuestionType = SurveyQuestionType.MULTIPLE_CHOICE
    options: List[str] = Field(..., min_length=2, max_length=10, description="Options")
    allow_multiple: bool = False  # Allow multiple selections
    next: Optional[str] = Field(None, description="Next question ID")
    # Option-based branching
    next_by_option: Optional[Dict[str, str]] = Field(None, description="Next question by option: {'Option A': 'q3a', 'Option B': 'q3b'}")


class SurveyQuestionRating(SurveyQuestionBase):
    """Rating/scoring question"""
    type: SurveyQuestionType = SurveyQuestionType.RATING
    min_value: int = Field(1, ge=0, le=10)
    max_value: int = Field(10, ge=1, le=100)
    min_label: Optional[str] = None  # e.g.: "Very bad"
    max_label: Optional[str] = None  # e.g.: "Excellent"
    next: Optional[str] = Field(None, description="Next question ID")
    # Score range-based branching
    next_by_range: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Branching by score range: [{'min': 1, 'max': 5, 'next': 'q_low'}, {'min': 6, 'max': 10, 'next': 'q_high'}]"
    )


class SurveyQuestionOpenEnded(SurveyQuestionBase):
    """Open-ended question"""
    type: SurveyQuestionType = SurveyQuestionType.OPEN_ENDED
    max_length: int = Field(500, ge=10, le=2000)
    placeholder: Optional[str] = None
    next: Optional[str] = Field(None, description="Next question ID")


class SurveyQuestion(BaseModel):
    """Unified question model - supports all types"""
    id: str
    type: SurveyQuestionType
    text: str
    required: bool = True
    # Options (for multiple_choice)
    options: Optional[List[str]] = None
    allow_multiple: bool = False
    # For rating
    min_value: int = 1
    max_value: int = 10
    min_label: Optional[str] = None
    max_label: Optional[str] = None
    # For open ended
    max_length: int = 500
    placeholder: Optional[str] = None
    # Branching
    next: Optional[str] = None  # Default next question
    next_on_yes: Optional[str] = None  # For Yes/No
    next_on_no: Optional[str] = None  # For Yes/No
    next_by_option: Optional[Dict[str, str]] = None  # Multiple choice option-based
    next_by_range: Optional[List[Dict[str, Any]]] = None  # Rating score-based


class SurveyConfig(BaseModel):
    """Agent survey configuration"""
    enabled: bool = False
    questions: List[SurveyQuestion] = Field(default_factory=list)
    start_question: Optional[str] = Field(None, description="Start question ID (default: first question)")
    completion_message: str = Field(
        default="Thank you for participating in our survey!",
        description="Message to say when survey is completed"
    )
    abort_message: str = Field(
        default="Survey cancelled, glad if I could help.",
        description="Message when survey is aborted"
    )
    allow_skip: bool = False  # Allow skipping questions
    show_progress: bool = True  # Show progress (e.g.: "3/5 questions")


class SurveyAnswerSubmit(BaseModel):
    """Survey answer submission (for tool call)"""
    question_id: str
    answer: str  # Answer text or value
    answer_value: Optional[Any] = None  # Numeric value (for rating)


class SurveyResponseCreate(BaseModel):
    """Create survey response"""
    call_id: Optional[int] = None
    agent_id: int
    campaign_id: Optional[int] = None
    respondent_phone: Optional[str] = None
    respondent_name: Optional[str] = None


class SurveyResponseUpdate(BaseModel):
    """Update survey response"""
    status: Optional[str] = None
    current_question_id: Optional[str] = None
    answers: Optional[List[Dict[str, Any]]] = None


class SurveyResponseResponse(BaseModel):
    """Survey response"""
    id: int
    call_id: Optional[int] = None
    agent_id: int
    campaign_id: Optional[int] = None
    respondent_phone: Optional[str] = None
    respondent_name: Optional[str] = None
    status: str
    answers: List[Dict[str, Any]]
    current_question_id: Optional[str] = None
    questions_answered: int
    total_questions: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None


class UltravoxVoiceSettings(BaseModel):
    """Ultravox-specific voice and VAD settings."""
    voice: str = "Mark"
    turn_endpoint_delay: float = Field(default=0.384, description="Seconds of silence before turn end")
    minimum_turn_duration: float = Field(default=0.0, description="Minimum turn duration in seconds")
    minimum_interruption_duration: float = Field(default=0.09, description="Min duration to count as interruption")
    frame_activation_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="VAD activation threshold")


class CallCost(BaseModel):
    """Unified cost response for both providers."""
    provider: str  # "openai", "ultravox", "xai", or "gemini"
    # OpenAI-specific (nullable)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    # Ultravox-specific
    rate_per_minute: Optional[float] = None
    # Common
    total_cost_usd: float


class AgentCreate(AgentBase):
    provider: str = "openai"  # "openai", "ultravox", "xai", or "gemini"
    voice_settings: Optional[VoiceSettings] = None
    call_settings: Optional[CallSettings] = None
    behavior_settings: Optional[BehaviorSettings] = None
    advanced_settings: Optional[AdvancedSettings] = None
    prompt: Optional[PromptSections] = None
    greeting_settings: Optional[GreetingSettings] = None
    inactivity_messages: Optional[List[InactivityMessage]] = None
    knowledge_base: Optional[str] = None
    web_sources: Optional[List[dict]] = None
    smart_features: Optional[SmartFeatures] = None
    survey_config: Optional[SurveyConfig] = None
    ultravox_settings: Optional[UltravoxVoiceSettings] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AgentStatus] = None
    provider: Optional[str] = None  # "openai", "ultravox", or "xai"
    voice_settings: Optional[VoiceSettings] = None
    call_settings: Optional[CallSettings] = None
    behavior_settings: Optional[BehaviorSettings] = None
    advanced_settings: Optional[AdvancedSettings] = None
    prompt: Optional[PromptSections] = None
    greeting_settings: Optional[GreetingSettings] = None
    inactivity_messages: Optional[List[InactivityMessage]] = None
    knowledge_base: Optional[str] = None  # Static knowledge base content
    web_sources: Optional[List[dict]] = None  # Web URLs: [{"url": "...", "name": "...", "description": "..."}]
    smart_features: Optional[SmartFeatures] = None
    survey_config: Optional[SurveyConfig] = None
    ultravox_settings: Optional[UltravoxVoiceSettings] = None


class AgentResponse(AgentBase):
    id: int
    provider: str = "openai"
    status: AgentStatus
    model_type: RealtimeModel = RealtimeModel.GPT_REALTIME_MINI
    voice: str
    language: str
    total_calls: int
    successful_calls: int
    is_system: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AgentDetailResponse(AgentResponse):
    # model_type is inherited from AgentResponse
    # Provider
    ultravox_agent_id: Optional[str] = None
    # Greeting settings
    first_speaker: str = "agent"
    greeting_message: Optional[str] = None
    greeting_uninterruptible: bool = False
    first_message_delay: float = 0.0
    inactivity_messages: Optional[List[Dict[str, Any]]] = None
    
    # Prompt sections (10-section standard structure)
    prompt_role: Optional[str] = None  # Role (who the agent is)
    prompt_personality: Optional[str] = None  # Environment (conversation context)
    prompt_context: Optional[str] = None  # Tone (how to speak)
    prompt_pronunciations: Optional[str] = None  # Goal (workflow steps)
    prompt_sample_phrases: Optional[str] = None  # Guardrails (non-negotiable rules)
    prompt_tools: Optional[str] = None  # Tools (when/how/error)
    prompt_rules: Optional[str] = None  # Instructions (format rules)
    prompt_flow: Optional[str] = None  # Conversation Flow (error recovery)
    prompt_safety: Optional[str] = None  # Safety & Escalation (emergency rules)
    prompt_language: Optional[str] = None  # Language (register guidelines)
    knowledge_base: Optional[str] = None  # Static knowledge base content
    web_sources: Optional[List[Dict[str, Any]]] = None  # Web URLs for dynamic info
    smart_features: Optional[Dict[str, Any]] = None  # Smart features
    survey_config: Optional[Dict[str, Any]] = None  # Survey configuration
    timezone: str = "Europe/Istanbul"
    speech_speed: float
    max_duration: int
    silence_timeout: int
    max_retries: int
    retry_delay: int
    interruptible: bool
    auto_transcribe: bool
    record_calls: bool
    human_transfer: bool
    temperature: float
    vad_threshold: float
    turn_detection: str
    vad_eagerness: str = "low"
    silence_duration_ms: int = 1000
    prefix_padding_ms: int = 400
    idle_timeout_ms: Optional[int] = None
    interrupt_response: bool = True
    create_response: bool = True
    noise_reduction: bool = True
    max_output_tokens: int = 500
    transcript_model: str = "gpt-4o-transcribe"


# ============ Campaign Schemas ============

class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None


class CampaignCreate(CampaignBase):
    agent_id: int
    number_list_id: int
    scheduled_start: Optional[datetime] = None
    call_hours_start: str = "09:00"
    call_hours_end: str = "20:00"
    active_days: List[int] = [1, 2, 3, 4, 5]
    concurrent_calls: int = Field(default=10, ge=1, le=50)

    @field_validator("call_hours_start", "call_hours_end")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format HH:MM"""
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format (e.g., 09:00, 20:00)")
        return v


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CampaignStatus] = None
    scheduled_start: Optional[datetime] = None
    call_hours_start: Optional[str] = None
    call_hours_end: Optional[str] = None
    concurrent_calls: Optional[int] = Field(default=None, ge=1, le=50)
    active_days: Optional[List[int]] = None

    @field_validator("call_hours_start", "call_hours_end")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate time format HH:MM"""
        if v is not None and not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", v):
            raise ValueError("Time must be in HH:MM format (e.g., 09:00, 20:00)")
        return v


class CampaignResponse(CampaignBase):
    id: int
    status: CampaignStatus
    agent_id: int
    total_numbers: int
    completed_calls: int
    successful_calls: int
    failed_calls: int = 0
    active_calls: int
    number_list_id: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    call_hours_start: Optional[str] = None
    call_hours_end: Optional[str] = None
    active_days: Optional[list] = None
    concurrent_calls: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Number List Schemas ============

class NumberListCreate(BaseModel):
    name: str


class NumberListResponse(BaseModel):
    id: int
    name: str
    file_name: Optional[str]
    total_numbers: int
    valid_numbers: int
    invalid_numbers: int
    duplicates: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PhoneNumberResponse(BaseModel):
    id: int
    phone: str
    name: Optional[str]
    is_valid: bool
    call_attempts: int
    last_outcome: Optional[CallOutcome]
    custom_data: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# ============ Call Log Schemas ============

class CallLogResponse(BaseModel):
    id: int
    call_sid: str
    provider: Optional[str] = None  # "openai" or "ultravox"
    ultravox_call_id: Optional[str] = None
    status: CallStatus
    outcome: Optional[CallOutcome] = None
    duration: int
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    customer_name: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    recording_url: Optional[str] = None
    transcription: Optional[str] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    campaign_id: Optional[int] = None
    agent_id: Optional[int] = None

    # Relationship names
    agent_name: Optional[str] = None
    campaign_name: Optional[str] = None

    # SIP details
    sip_code: Optional[int] = None
    hangup_cause: Optional[str] = None

    # AMD
    amd_status: Optional[str] = None  # HUMAN, MACHINE, NOTSURE
    amd_cause: Optional[str] = None  # AMD decision reason

    # Tags
    tags: Optional[list] = None

    # Cost tracking
    model_used: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost: float = 0.0

    connected_at: Optional[datetime] = None
    notes: Optional[str] = None
    intent: Optional[str] = None
    callback_scheduled: Optional[datetime] = None
    call_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CallCostSummary(BaseModel):
    """Summary of call costs for reporting"""
    total_calls: int
    total_duration_seconds: int
    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_cost_usd: float
    avg_cost_per_call: float
    avg_cost_per_minute: float
    model_breakdown: Dict[str, Any]  # Costs per model type


# ============ Recording Schemas ============

class RecordingResponse(BaseModel):
    id: int
    call_sid: str
    to_number: str
    customer_name: Optional[str]
    campaign_name: Optional[str]
    agent_name: Optional[str]
    duration: int
    status: str
    sentiment: Optional[str]
    recording_url: Optional[str]
    transcription: Optional[str]
    created_at: datetime


# ============ Settings Schemas ============

class PagePermissions(BaseModel):
    """Page-level access permissions for a role"""
    dashboard: bool = True
    agents: bool = True
    campaigns: bool = True
    numbers: bool = True
    recordings: bool = True
    call_logs: bool = True
    appointments: bool = True
    leads: bool = True
    surveys: bool = True
    reports: bool = True
    settings: bool = True


class RolePermissionResponse(BaseModel):
    id: int
    role: str
    permissions: PagePermissions
    description: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RolePermissionUpdate(BaseModel):
    permissions: PagePermissions
    description: Optional[str] = None


class SIPTrunkCreate(BaseModel):
    name: str
    server: str
    port: int = 5060
    username: Optional[str] = None
    password: Optional[str] = None
    transport: str = "udp"
    codec_priority: str = "opus"
    concurrent_limit: int = 50


class SIPTrunkResponse(BaseModel):
    id: int
    name: str
    server: str
    port: int
    transport: str
    concurrent_limit: int
    is_active: bool
    is_connected: bool
    codec_priority: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WebhookCreate(BaseModel):
    url: str
    events: List[str]


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    total_deliveries: int
    failed_deliveries: int
    last_error: Optional[str] = None
    last_delivery_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Stats Schemas ============

class DashboardStats(BaseModel):
    active_calls: int
    today_calls: int
    success_rate: float
    avg_duration: float
    active_campaigns: int
    total_agents: int
    active_calls_change: float = 0
    today_calls_change: float = 0
    success_rate_change: float = 0
    avg_duration_change: float = 0


class CallStats(BaseModel):
    total: int
    successful: int
    failed: int
    transferred: int
    no_answer: int
    avg_duration: float


# ============ Pagination ============

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ============ Standard API Response ============

class APIResponse(BaseModel):
    """Standard API response wrapper for consistency"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class APIErrorResponse(BaseModel):
    """Standard API error response"""
    success: bool = False
    detail: str
    error_code: Optional[str] = None
    request_id: Optional[str] = None


# ============ Agent Document Schemas (RAG) ============

class AgentDocumentCreate(BaseModel):
    """Used internally when creating document record"""
    filename: str
    file_type: str
    file_size: int
    file_path: Optional[str] = None


class AgentDocumentResponse(BaseModel):
    """Document response for API"""
    id: int
    agent_id: int
    filename: str
    file_type: str
    file_size: int
    status: str  # pending, processing, ready, error
    error_message: Optional[str] = None
    chunk_count: int = 0
    token_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentChunkResponse(BaseModel):
    """Chunk response for search results"""
    id: int
    content: str
    chunk_index: int
    score: Optional[float] = None  # Similarity score
    document_filename: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentSearchRequest(BaseModel):
    """Search request for document chunks"""
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class DocumentSearchResponse(BaseModel):
    """Search response with relevant chunks"""
    query: str
    results: List[DocumentChunkResponse]
    total_found: int


# ============ Appointment Schemas ============

class AppointmentCreate(BaseModel):
    """Create appointment (from AI tool call)"""
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    appointment_type: AppointmentType = AppointmentType.CONSULTATION
    appointment_date: datetime
    appointment_time: Optional[str] = None
    duration_minutes: int = 60
    notes: Optional[str] = None
    location: Optional[str] = None
    
    # Call context
    call_id: Optional[int] = None
    agent_id: Optional[int] = None
    campaign_id: Optional[int] = None


class AppointmentUpdate(BaseModel):
    """Update appointment"""
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    appointment_type: Optional[AppointmentType] = None
    appointment_date: Optional[datetime] = None
    appointment_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    location: Optional[str] = None


class AppointmentResponse(BaseModel):
    """Appointment response"""
    id: int
    call_id: Optional[int] = None
    agent_id: Optional[int] = None
    campaign_id: Optional[int] = None
    
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    
    appointment_type: AppointmentType
    appointment_date: datetime
    appointment_time: Optional[str] = None
    duration_minutes: int
    
    status: AppointmentStatus
    notes: Optional[str] = None
    location: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    
    # Related info (joined)
    agent_name: Optional[str] = None
    campaign_name: Optional[str] = None

    class Config:
        from_attributes = True


class AppointmentListResponse(BaseModel):
    """Paginated appointment list"""
    items: List[AppointmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============ Lead Schemas ============

class LeadCreate(BaseModel):
    """Create a new lead"""
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    interest_type: LeadInterestType = LeadInterestType.CALLBACK
    customer_statement: Optional[str] = None
    notes: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=3)
    source: Optional[str] = None


class LeadUpdate(BaseModel):
    """Update lead"""
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    interest_type: Optional[LeadInterestType] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    next_follow_up: Optional[datetime] = None


class LeadResponse(BaseModel):
    """Lead response"""
    id: int
    call_id: Optional[int] = None
    agent_id: Optional[int] = None
    campaign_id: Optional[int] = None
    
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    
    interest_type: LeadInterestType
    status: LeadStatus
    customer_statement: Optional[str] = None
    notes: Optional[str] = None
    priority: int
    source: Optional[str] = None
    
    last_contacted_at: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None
    follow_up_count: int
    
    created_at: datetime
    updated_at: datetime
    converted_at: Optional[datetime] = None
    
    # Related info (joined)
    agent_name: Optional[str] = None
    campaign_name: Optional[str] = None

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Paginated lead list"""
    items: List[LeadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class LeadStats(BaseModel):
    """Lead statistics"""
    total: int
    today: int
    by_status: Dict[str, int]
    by_interest_type: Dict[str, int]
    by_priority: Dict[str, int]


# ============ Call Tags Schemas ============

class CallTagsUpdate(BaseModel):
    """Update call tags"""
    tags: List[str] = Field(default_factory=list)
    operation: str = Field(default="add", description="Tag operation: add, remove, or set")

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        """Validate operation is one of the allowed values"""
        allowed = {"add", "remove", "set"}
        if v not in allowed:
            raise ValueError(f"Invalid operation: {v}. Allowed: {allowed}")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tags are valid CallTag enum values"""
        valid_tags = [t.value for t in CallTag]
        for tag in v:
            if tag not in valid_tags:
                raise ValueError(f"Invalid tag: {tag}. Valid tags: {valid_tags}")
        return v


class CallTagsResponse(BaseModel):
    """Call tags response"""
    call_id: str
    tags: List[str]


# ============ ViciDial-Style Dialing Schemas ============

class DialListCreate(BaseModel):
    """Create a new dial list"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class DialListUpdate(BaseModel):
    """Update a dial list"""
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    status: Optional[DialListStatus] = None


class DialListResponse(BaseModel):
    """Dial list response"""
    id: int
    name: str
    description: Optional[str] = None
    status: str
    total_numbers: int
    active_numbers: int
    completed_numbers: int
    invalid_numbers: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DialListEntryCreate(BaseModel):
    """Create a single dial list entry"""
    phone_number: str = Field(..., min_length=1, max_length=20)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    company: Optional[str] = Field(default=None, max_length=255)
    timezone: Optional[str] = Field(default=None, max_length=50)
    priority: int = Field(default=0, ge=0, le=100)
    max_attempts: int = Field(default=3, ge=1, le=20)
    custom_fields: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class DialListEntryUpdate(BaseModel):
    """Update a dial list entry"""
    status: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=0, le=100)
    next_callback_at: Optional[datetime] = None
    dnc_flag: Optional[bool] = None


class DialListEntryBulkCreate(BaseModel):
    """Bulk create dial list entries (e.g., from Excel upload)"""
    entries: List[DialListEntryCreate] = Field(..., min_length=1, max_length=10000)


class DialListEntryResponse(BaseModel):
    """Dial list entry response"""
    id: int
    list_id: int
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    priority: int
    status: str
    call_attempts: int
    max_attempts: int
    last_attempt_at: Optional[datetime] = None
    next_callback_at: Optional[datetime] = None
    dnc_flag: bool
    custom_fields: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DialAttemptResponse(BaseModel):
    """Dial attempt response"""
    id: int
    entry_id: int
    campaign_id: int
    call_log_id: Optional[int] = None
    attempt_number: int
    result: str
    sip_code: Optional[int] = None
    hangup_cause: Optional[str] = None
    duration: int
    started_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DNCListCreate(BaseModel):
    """Add a number to DNC list"""
    phone_number: str = Field(..., min_length=1, max_length=20)
    source: Optional[str] = Field(default="manual", max_length=50)
    reason: Optional[str] = None


class DNCListResponse(BaseModel):
    """DNC list entry response"""
    id: int
    phone_number: str
    source: Optional[str] = None
    reason: Optional[str] = None
    added_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignListCreate(BaseModel):
    """Link a dial list to a campaign"""
    campaign_id: int
    list_id: int
    priority: int = Field(default=0, ge=0, le=100)
    active: bool = True


class CampaignListResponse(BaseModel):
    """Campaign-list link response"""
    id: int
    campaign_id: int
    list_id: int
    priority: int
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DialHopperResponse(BaseModel):
    """Dial hopper entry response"""
    id: int
    campaign_id: int
    entry_id: int
    priority: int
    status: str
    inserted_at: datetime

    class Config:
        from_attributes = True


class CampaignDispositionCreate(BaseModel):
    """Create a campaign disposition"""
    campaign_id: int
    name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)
    next_action: Optional[str] = Field(default="none", max_length=50)
    retry_delay_minutes: int = Field(default=60, ge=1, le=10080)
    is_final: bool = False


class CampaignDispositionResponse(BaseModel):
    """Campaign disposition response"""
    id: int
    campaign_id: int
    name: str
    category: Optional[str] = None
    next_action: Optional[str] = None
    retry_delay_minutes: int
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ExcelUploadResponse(BaseModel):
    """Response for Excel/CSV file upload results"""
    total: int
    success: int
    errors: int
    duplicates: int
    error_details: Optional[List[Dict[str, Any]]] = None


# ============ Agent Tariff Schemas ============

class AgentTariffCreate(BaseModel):
    """Create a tariff rule for an agent."""
    prefix: str = Field(..., min_length=1, max_length=20, description="Number prefix, e.g. '49', '495'")
    price_per_second: float = Field(..., gt=0, description="Price per second for this prefix")
    description: Optional[str] = Field(default=None, max_length=255, description="Human-readable label")


class AgentTariffUpdate(BaseModel):
    """Update a tariff rule."""
    prefix: Optional[str] = Field(default=None, min_length=1, max_length=20)
    price_per_second: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, max_length=255)


class AgentTariffResponse(BaseModel):
    """Tariff rule response."""
    id: int
    agent_id: int
    prefix: str
    price_per_second: float
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentCallLogItem(BaseModel):
    """Single call entry in agent call log with tariff cost."""
    id: int
    call_sid: str
    to_number: Optional[str] = None
    from_number: Optional[str] = None
    customer_name: Optional[str] = None
    status: str
    outcome: Optional[str] = None
    duration: int  # seconds
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    campaign_name: Optional[str] = None
    provider: Optional[str] = None
    # Tariff cost
    matched_prefix: Optional[str] = None
    price_per_second: Optional[float] = None
    tariff_cost: Optional[float] = None  # duration * price_per_second
    tariff_description: Optional[str] = None
    # Transcript / Summary
    summary: Optional[str] = None
    has_transcription: bool = False


class AgentCallLogResponse(BaseModel):
    """Paginated agent call log with tariff cost summary."""
    items: List[AgentCallLogItem]
    total: int
    page: int
    page_size: int
    # Summary
    total_duration_seconds: int
    total_tariff_cost: float
    avg_cost_per_call: float
