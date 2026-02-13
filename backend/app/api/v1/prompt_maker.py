"""
Prompt Maker API — Provider-aware voice agent prompt generation
Uses GPT-4o to create prompts optimized for each AI provider's architecture.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

import httpx
import os
import logging

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.models import User, Agent, PromptHistory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prompt-maker", tags=["Prompt Maker"])


# ─── Request / Response Models ────────────────────────────────────

class PromptMakerRequest(BaseModel):
    """Input form for prompt generation"""
    provider: str = Field(..., description="Target provider: openai, ultravox, xai, gemini")
    title: str = Field(..., min_length=2, max_length=255, description="Short name for this prompt")
    description: str = Field(..., min_length=10, max_length=3000, description="What the agent should do")
    agent_type: Optional[str] = Field(default=None, description="sales, support, collection, appointment, survey")
    tone: Optional[str] = Field(default="professional", description="professional, friendly, formal, casual")
    language: str = Field(default="en", description="Prompt language: en, tr, de, etc.")
    company_name: Optional[str] = Field(default=None, description="Company name for context")
    industry: Optional[str] = Field(default=None, description="Industry / sector")
    tools_description: Optional[str] = Field(default=None, description="Tools the agent should use")
    constraints: Optional[str] = Field(default=None, description="Things the agent must NOT do")
    example_dialogue: Optional[str] = Field(default=None, description="Sample conversation snippet")


class PromptMakerResponse(BaseModel):
    """Generated prompt result"""
    id: int
    title: str
    provider: str
    generated_prompt: str
    tips: List[str] = []
    created_at: datetime


class PromptHistoryItem(BaseModel):
    id: int
    title: str
    provider: str
    agent_type: Optional[str]
    language: str
    description: Optional[str]
    generated_prompt: str
    applied_to_agent_id: Optional[int]
    applied_to_agent_name: Optional[str] = None
    created_at: datetime


class PromptHistoryListResponse(BaseModel):
    items: List[PromptHistoryItem]
    total: int


class ApplyToAgentRequest(BaseModel):
    agent_id: int


# ─── Provider-specific System Prompts for GPT-4o ──────────────────

OPENAI_SYSTEM_PROMPT = """You are an expert prompt engineer specializing in OpenAI Realtime API voice agents.

## OPENAI REALTIME API — KEY CHARACTERISTICS:
- Uses `instructions` field (equivalent to system prompt)
- Token-based billing (audio tokens are expensive) — prompts MUST be concise
- Supports turn detection with VAD (Voice Activity Detection)
- Native audio understanding — model processes speech directly
- Server-sent events architecture with WebSocket
- Supports function calling / tool use
- Models: gpt-4o-realtime-preview, gpt-4o-mini-realtime-preview

## OPENAI VOICE-SPECIFIC BEST PRACTICES:
- Keep prompts SHORT — 1000-2000 characters ideal. Longer prompts = higher cost per turn
- Use clear, imperative sentences — the model follows instructions literally
- Always include "respond in 1-2 sentences" — prevents monologuing
- Specify "you are on a phone call" context — model adjusts for latency
- Use "STOP and WAIT" for turn-taking — critical for voice
- Avoid markdown formatting in output — model speaks everything
- Numbers: instruct to say "one two three" not "123"
- Include silence handling: "If silence > 3 seconds, ask if they're still there"

## REQUIRED STRUCTURE (use # markdown headings):
# Role
# Environment
# Tone
# Goal
# Guardrails
# Tools (if applicable)
# Instructions
# Conversation Flow
# Safety & Escalation
# Language

## RULES:
1. Target 1500-2500 characters total — OpenAI charges per token, shorter = cheaper
2. Use bullet points, not paragraphs
3. Mark critical rules with "This step is important."
4. Always include voice interaction rules in Guardrails
5. Write in the language specified by the user
6. Optimize for real-time audio — avoid complex formatting instructions"""

ULTRAVOX_SYSTEM_PROMPT = """You are an expert prompt engineer specializing in Ultravox voice AI agents.

## ULTRAVOX PLATFORM — KEY CHARACTERISTICS:
- Built on Llama 3.3 70B (frozen during training) — prompt as if text LLM
- Uses `systemPrompt` field
- NO default prompt appended — you must provide complete instructions
- Supports template variables: {{agentName}}, {{companyName}}, etc.
- Supports `<instruction>` tags for high-priority directives
- Deciminute billing ($0.005/6s) — prompt length doesn't affect cost directly
- Native multimodal: hears audio directly, no separate STT step
- Supports tool calling with detailed tool definitions

## ULTRAVOX-SPECIFIC BEST PRACTICES:
- Can use LONGER, more detailed prompts than OpenAI (cost isn't per-token)
- Use `<instruction>` tags for critical rules the agent must always follow
- Use "..." (ellipsis) to create natural pauses: "Wow, that's interesting... tell me more...?"
- Numbers: "Output as individual digits separated by hyphens (1234 → '1-2-3-4')"
- Dates: "Output as components (12/25/2022 → 'December twenty-fifth twenty twenty-two')"
- Tell model explicitly "You're interacting over voice, speak casually"
- Use examples (few-shot) — Llama learns very well from examples
- Jailbreak prevention: "Your only job is [X]. If asked something unrelated, politely decline."
- Step-by-step: give one instruction at a time, wait for user confirmation
- Be literal and specific — Llama is a very literal instruction follower
- Start simple, iterate based on testing

## REQUIRED STRUCTURE (use # markdown headings):
# Role
# Environment
# Tone
# Goal
# Guardrails
# Tools (if applicable)
# Instructions
# Conversation Flow
# Safety & Escalation
# Language

## RULES:
1. Can be longer than OpenAI prompts — 2000-4000 characters is fine
2. Use few-shot examples where helpful
3. Use `<instruction>` tags for critical rules
4. Use "..." for natural speech pauses
5. Format numbers/dates for speech output
6. Include voice-specific context ("this is a phone call")
7. Write in the language specified by the user"""

XAI_SYSTEM_PROMPT = """You are an expert prompt engineer specializing in xAI Grok Realtime voice agents.

## XAI GROK REALTIME — KEY CHARACTERISTICS:
- OpenAI-compatible API (same WebSocket protocol as OpenAI Realtime)
- Uses `instructions` field (same as OpenAI)
- Per-second billing ($0.05/min) — prompt length doesn't affect cost
- Based on Grok model — more conversational and less rigid than GPT-4o
- Supports function calling (OpenAI-compatible format)
- Good at following conversational instructions
- More tolerant of longer prompts than OpenAI

## XAI GROK-SPECIFIC BEST PRACTICES:
- Grok is naturally more conversational — lean into that
- Can handle longer prompts than OpenAI without quality loss
- Grok follows instructions well but is less strict — reinforce critical rules
- Good at maintaining personality throughout long conversations
- Use natural language for instructions more than rigid formatting
- Grok handles humor and casual tone very well
- Still needs voice-specific rules (1-2 sentences, wait for response, etc.)
- Tool calling follows OpenAI format — same When/Parameters/Usage pattern

## REQUIRED STRUCTURE (use # markdown headings):
# Role
# Environment
# Tone
# Goal
# Guardrails
# Tools (if applicable)
# Instructions
# Conversation Flow
# Safety & Escalation
# Language

## RULES:
1. Target 2000-3500 characters — Grok handles medium-length prompts well
2. Use natural, conversational instruction style
3. Reinforce critical rules with "You MUST always..." or "NEVER..."
4. Include voice interaction rules
5. Write in the language specified by the user
6. Grok excels at personality — spend more words on personality section"""

GEMINI_SYSTEM_PROMPT = """You are an expert prompt engineer specializing in Google Gemini Live API voice agents.

## GEMINI LIVE API — KEY CHARACTERISTICS:
- Uses `system_instruction` field (similar to system prompt)
- Native audio model — processes speech directly (no separate STT/TTS)
- Built on Gemini 2.0 Flash — very fast, multimodal
- WebSocket-based streaming (server-to-server or client-to-server)
- Supports function calling and tool use
- Voice Activity Detection (VAD) built in
- Token-based billing (audio + text tokens)
- Supports multiple response modalities (audio, text)

## GEMINI-SPECIFIC BEST PRACTICES:
- Gemini is highly structured — benefits from well-organized prompts
- Use clear section headers for different aspects of behavior
- Gemini handles complex multi-step instructions well
- Good at following safety guidelines strictly
- Supports grounding with Google Search — mention if relevant
- Keep audio output instructions explicit: "respond naturally as in a phone call"
- Gemini can handle both short and medium-length prompts
- Function calling is native — provide clear tool descriptions
- Reference "this is a real-time voice conversation" for modality awareness
- Specify response format: "Keep responses under 2 sentences for voice"

## REQUIRED STRUCTURE (use # markdown headings):
# Role
# Environment
# Tone
# Goal
# Guardrails
# Tools (if applicable)
# Instructions
# Conversation Flow
# Safety & Escalation
# Language

## RULES:
1. Target 1500-3000 characters
2. Structured, clear sections with headers
3. Explicit voice formatting rules (numbers, dates, etc.)
4. Strong safety section — Gemini respects safety instructions well
5. Include modality-aware context ("this is real-time audio")
6. Write in the language specified by the user"""


# Map provider to its specialized system prompt
PROVIDER_PROMPTS = {
    "openai": OPENAI_SYSTEM_PROMPT,
    "ultravox": ULTRAVOX_SYSTEM_PROMPT,
    "xai": XAI_SYSTEM_PROMPT,
    "gemini": GEMINI_SYSTEM_PROMPT,
}

PROVIDER_TIPS = {
    "openai": [
        "OpenAI Realtime charges per audio token — keep this prompt concise",
        "Test with gpt-4o-mini-realtime for lower cost during development",
        "Use 'This step is important.' to emphasize critical rules",
        "Shorter prompts generally perform better with OpenAI Realtime",
    ],
    "ultravox": [
        "Ultravox uses Llama 3.3 70B — prompt it like a text model",
        "Use <instruction> tags for rules the agent must never break",
        "Add '...' in example responses to create natural speech pauses",
        "Ultravox doesn't add default prompts — everything must be explicit",
        "Longer, more detailed prompts work well with Ultravox (cost is time-based)",
    ],
    "xai": [
        "Grok is naturally conversational — it handles personality very well",
        "xAI bills per second, not per token — prompt length doesn't affect cost",
        "Grok can be less strict than GPT-4o — reinforce critical rules with MUST/NEVER",
        "Great for agents that need humor or casual personality",
    ],
    "gemini": [
        "Gemini 2.0 Flash is very fast — ideal for real-time conversations",
        "Gemini follows safety instructions strictly — use this for sensitive domains",
        "Native audio keeps latency low — no separate STT/TTS pipeline",
        "Well-structured prompts with clear headers work best with Gemini",
    ],
}


# ─── API Endpoints ────────────────────────────────────────────────

@router.post("/generate", response_model=PromptMakerResponse)
async def generate_prompt(
    request: PromptMakerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a provider-optimized prompt using GPT-4o"""
    if request.provider not in PROVIDER_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(PROVIDER_PROMPTS.keys())}",
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    # Build the user message from form fields
    parts = [f"Description: {request.description}"]
    if request.company_name:
        parts.append(f"Company: {request.company_name}")
    if request.industry:
        parts.append(f"Industry: {request.industry}")

    agent_type_labels = {
        "sales": "Sales representative",
        "support": "Customer support",
        "collection": "Collections / payment reminder",
        "appointment": "Appointment scheduling",
        "survey": "Survey / feedback collection",
    }
    if request.agent_type:
        parts.append(f"Agent type: {agent_type_labels.get(request.agent_type, request.agent_type)}")

    tone_labels = {
        "professional": "Professional and business-like",
        "friendly": "Friendly and warm",
        "formal": "Formal and structured",
        "casual": "Casual and relaxed",
    }
    if request.tone:
        parts.append(f"Tone: {tone_labels.get(request.tone, request.tone)}")

    parts.append(f"Language: {request.language}")

    if request.tools_description:
        parts.append(f"Tools available: {request.tools_description}")
    if request.constraints:
        parts.append(f"Constraints / things to avoid: {request.constraints}")
    if request.example_dialogue:
        parts.append(f"Example dialogue:\n{request.example_dialogue}")

    user_message = "\n".join(parts)
    system_prompt = PROVIDER_PROMPTS[request.provider]

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 3000,
                },
            )

            if response.status_code != 200:
                logger.error(f"OpenAI API error: {response.text}")
                raise HTTPException(status_code=502, detail="AI generation service error")

            data = response.json()
            generated = data["choices"][0]["message"]["content"]

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI generation timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate prompt")

    # Save to DB
    history = PromptHistory(
        title=request.title,
        provider=request.provider,
        agent_type=request.agent_type,
        tone=request.tone,
        language=request.language,
        description=request.description,
        generated_prompt=generated,
        owner_id=current_user.id,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return PromptMakerResponse(
        id=history.id,
        title=history.title,
        provider=history.provider,
        generated_prompt=history.generated_prompt,
        tips=PROVIDER_TIPS.get(request.provider, []),
        created_at=history.created_at,
    )


@router.get("/history", response_model=PromptHistoryListResponse)
async def list_prompt_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    provider: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's generated prompts"""
    query = db.query(PromptHistory).filter(PromptHistory.owner_id == current_user.id)

    if provider:
        query = query.filter(PromptHistory.provider == provider)

    total = query.count()
    rows = (
        query.order_by(PromptHistory.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for row in rows:
        agent_name = None
        if row.applied_to_agent_id:
            agent = db.query(Agent).filter(Agent.id == row.applied_to_agent_id).first()
            agent_name = agent.name if agent else None

        items.append(
            PromptHistoryItem(
                id=row.id,
                title=row.title,
                provider=row.provider,
                agent_type=row.agent_type,
                language=row.language,
                description=row.description,
                generated_prompt=row.generated_prompt,
                applied_to_agent_id=row.applied_to_agent_id,
                applied_to_agent_name=agent_name,
                created_at=row.created_at,
            )
        )

    return PromptHistoryListResponse(items=items, total=total)


@router.get("/history/{prompt_id}", response_model=PromptHistoryItem)
async def get_prompt_detail(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single prompt from history"""
    row = (
        db.query(PromptHistory)
        .filter(PromptHistory.id == prompt_id, PromptHistory.owner_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found")

    agent_name = None
    if row.applied_to_agent_id:
        agent = db.query(Agent).filter(Agent.id == row.applied_to_agent_id).first()
        agent_name = agent.name if agent else None

    return PromptHistoryItem(
        id=row.id,
        title=row.title,
        provider=row.provider,
        agent_type=row.agent_type,
        language=row.language,
        description=row.description,
        generated_prompt=row.generated_prompt,
        applied_to_agent_id=row.applied_to_agent_id,
        applied_to_agent_name=agent_name,
        created_at=row.created_at,
    )


@router.delete("/history/{prompt_id}")
async def delete_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a prompt from history"""
    row = (
        db.query(PromptHistory)
        .filter(PromptHistory.id == prompt_id, PromptHistory.owner_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Prompt not found")

    db.delete(row)
    db.commit()
    return {"success": True}


@router.post("/history/{prompt_id}/apply")
async def apply_prompt_to_agent(
    prompt_id: int,
    request: ApplyToAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply a generated prompt to an existing agent's system prompt"""
    # Verify prompt ownership
    prompt_row = (
        db.query(PromptHistory)
        .filter(PromptHistory.id == prompt_id, PromptHistory.owner_id == current_user.id)
        .first()
    )
    if not prompt_row:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Verify agent ownership
    agent = (
        db.query(Agent)
        .filter(Agent.id == request.agent_id, Agent.owner_id == current_user.id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Parse the generated prompt into 10 sections
    sections = _parse_prompt_sections(prompt_row.generated_prompt)

    # Apply sections to agent model fields
    agent.prompt_role = sections.get("role", "")
    agent.prompt_personality = sections.get("personality", "")
    agent.prompt_context = sections.get("context", "")
    agent.prompt_pronunciations = sections.get("pronunciations", "")
    agent.prompt_sample_phrases = sections.get("sample_phrases", "")
    agent.prompt_tools = sections.get("tools", "")
    agent.prompt_rules = sections.get("rules", "")
    agent.prompt_flow = sections.get("flow", "")
    agent.prompt_safety = sections.get("safety", "")
    agent.prompt_language = sections.get("language", "")

    # Record which agent this prompt was applied to
    prompt_row.applied_to_agent_id = request.agent_id

    db.commit()

    logger.info(
        f"Prompt {prompt_id} applied to agent {request.agent_id} "
        f"by user {current_user.id}"
    )

    return {
        "success": True,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "message": f"Prompt applied to agent '{agent.name}'",
    }


def _parse_prompt_sections(prompt_text: str) -> dict:
    """
    Parse a markdown-headed prompt into the 10 DB section fields.
    Maps various heading names to the correct DB column.
    """
    # Heading → DB field mapping (supports multiple naming conventions)
    heading_map = {
        # DB field: prompt_role
        "role": "role",
        "agent identity": "role",
        "agent role": "role",
        "role & personality": "role",
        # DB field: prompt_personality (stores Environment)
        "environment": "personality",
        "voice interaction context": "personality",
        "conversation context": "personality",
        "context": "personality",
        # DB field: prompt_context (stores Tone)
        "tone": "context",
        "personality & tone": "context",
        "tone & style": "context",
        "tone & communication style": "context",
        # DB field: prompt_pronunciations (stores Goal)
        "goal": "pronunciations",
        "workflow steps": "pronunciations",
        # DB field: prompt_sample_phrases (stores Guardrails)
        "guardrails": "sample_phrases",
        "guardrails & rules": "sample_phrases",
        # DB field: prompt_tools
        "tools": "tools",
        "tool usage": "tools",
        "tool definitions": "tools",
        # DB field: prompt_rules (stores Instructions)
        "instructions": "rules",
        "response guidelines": "rules",
        "speech formatting": "rules",
        "voice output formatting": "rules",
        # DB field: prompt_flow (stores Conversation Flow)
        "conversation flow": "flow",
        "error handling": "flow",
        "error recovery": "flow",
        # DB field: prompt_safety
        "safety & escalation": "safety",
        "safety": "safety",
        # DB field: prompt_language
        "language": "language",
        "language settings": "language",
    }

    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in prompt_text.split("\n"):
        stripped = line.strip()

        # Check for # heading
        if stripped.startswith("# ") and not stripped.startswith("## "):
            # Save previous section
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()

            heading = stripped[2:].strip().lower()
            current_key = heading_map.get(heading)
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections
