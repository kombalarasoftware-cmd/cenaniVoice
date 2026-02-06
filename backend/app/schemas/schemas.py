"""
Pydantic schemas for request/response validation.
Enums are imported from models to maintain single source of truth.
"""

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
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Auth Schemas ============

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ============ Agent Schemas ============

class PromptSections(BaseModel):
    role: Optional[str] = None
    personality: Optional[str] = None
    language: Optional[str] = None
    flow: Optional[str] = None
    tools: Optional[str] = None
    safety: Optional[str] = None
    rules: Optional[str] = None


class VoiceSettings(BaseModel):
    model_type: RealtimeModel = RealtimeModel.GPT_REALTIME_MINI  # Default to economic
    voice: str = "alloy"
    language: str = "tr"
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
    vad_threshold: float = Field(default=0.5, ge=0, le=1)
    turn_detection: str = "server_vad"


class GreetingSettings(BaseModel):
    first_speaker: str = "agent"  # 'agent' or 'user'
    greeting_message: Optional[str] = None
    greeting_uninterruptible: bool = False
    first_message_delay: float = 0.0


class InactivityMessage(BaseModel):
    duration: int = 30
    message: str = ""
    end_behavior: str = "unspecified"  # 'unspecified', 'interruptible_hangup', 'uninterruptible_hangup'


class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None


class AgentCreate(AgentBase):
    voice_settings: Optional[VoiceSettings] = None
    call_settings: Optional[CallSettings] = None
    behavior_settings: Optional[BehaviorSettings] = None
    advanced_settings: Optional[AdvancedSettings] = None
    prompt: Optional[PromptSections] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AgentStatus] = None
    voice_settings: Optional[VoiceSettings] = None
    call_settings: Optional[CallSettings] = None
    behavior_settings: Optional[BehaviorSettings] = None
    advanced_settings: Optional[AdvancedSettings] = None
    prompt: Optional[PromptSections] = None
    greeting_settings: Optional[GreetingSettings] = None
    inactivity_messages: Optional[List[InactivityMessage]] = None


class AgentResponse(AgentBase):
    id: int
    status: AgentStatus
    model_type: RealtimeModel = RealtimeModel.GPT_REALTIME_MINI
    voice: str
    language: str
    total_calls: int
    successful_calls: int
    created_at: datetime

    class Config:
        from_attributes = True


class AgentDetailResponse(AgentResponse):
    # model_type is inherited from AgentResponse
    # Greeting settings
    first_speaker: str = "agent"
    greeting_message: Optional[str] = None
    greeting_uninterruptible: bool = False
    first_message_delay: float = 0.0
    inactivity_messages: Optional[List[Dict[str, Any]]] = None
    
    # Prompt sections
    prompt_role: Optional[str]
    prompt_personality: Optional[str]
    prompt_language: Optional[str]
    prompt_flow: Optional[str]
    prompt_tools: Optional[str]
    prompt_safety: Optional[str]
    prompt_rules: Optional[str]

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
    active_calls: int
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
    status: CallStatus
    outcome: Optional[CallOutcome]
    duration: int
    from_number: Optional[str]
    to_number: Optional[str]
    customer_name: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    recording_url: Optional[str]
    transcription: Optional[str]
    sentiment: Optional[str]
    campaign_id: Optional[int]

    # Cost tracking
    model_used: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost: float = 0.0

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
    phone_number: str
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
