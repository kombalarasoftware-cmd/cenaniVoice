"""
Pipeline call provider implementation.

Implements the CallProvider interface using cloud AI pipeline:
  - STT: Deepgram, OpenAI
  - LLM: Groq, OpenAI, Cerebras
  - TTS: Cartesia, OpenAI, Deepgram

Uses Asterisk AudioSocket (same as OpenAI provider) but connects
to pipeline-bridge instead of asterisk-bridge.
"""

import json
import logging
import uuid as uuid_lib
from typing import Any, Optional

import aiohttp
import redis

from app.core.config import settings
from app.services.call_provider import CallProvider
from app.services.greeting_processor import process_greeting

logger = logging.getLogger(__name__)

# Redis client for call tracking
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

# Asterisk ARI config
ARI_HOST = settings.ASTERISK_HOST
ARI_PORT = settings.ASTERISK_ARI_PORT
ARI_USERNAME = settings.ASTERISK_ARI_USER
ARI_PASSWORD = settings.ASTERISK_ARI_PASSWORD

# Cloud pipeline pricing (pay-per-use, estimated per minute)
PIPELINE_RATE_PER_MINUTE = 0.005


class PipelineProvider(CallProvider):
    """
    Call provider using cloud STT + LLM + TTS pipeline.

    Uses Asterisk AudioSocket (like OpenAI provider) but routes
    to pipeline-bridge on port 9093 instead of asterisk-bridge on 9092.

    Flow:
    1. Store agent config in Redis (with cloud provider settings)
    2. Call Asterisk ARI to originate channel in 'ai-outbound-pipeline' context
    3. pipeline_bridge.py handles: AudioSocket ↔ Cloud STT ↔ Cloud LLM ↔ Cloud TTS
    """

    async def initiate_call(
        self,
        agent: Any,
        phone_number: str,
        caller_id: str,
        customer_name: str = "",
        customer_title: str = "",
        conversation_history: str = "",
        campaign_id: Optional[int] = None,
        variables: Optional[dict] = None,
    ) -> dict:
        """Initiate call via Asterisk ARI, routing to pipeline bridge."""
        call_uuid = str(uuid_lib.uuid4())

        channel_variables = {
            "VOICEAI_UUID": call_uuid,
        }

        if agent:
            # Build prompt from sections (same structure as OpenAI)
            prompt_parts = []
            section_map = [
                ("Personality", "prompt_role"),
                ("Environment", "prompt_personality"),
                ("Tone", "prompt_context"),
                ("Goal", "prompt_pronunciations"),
                ("Guardrails", "prompt_sample_phrases"),
                ("Tools", "prompt_tools"),
                ("Character normalization", "prompt_rules"),
                ("Error handling", "prompt_flow"),
                ("Safety", "prompt_safety"),
                ("Language", "prompt_language"),
            ]
            for heading, attr in section_map:
                content = getattr(agent, attr, None)
                if content:
                    prompt_parts.append(f"# {heading}\n{content}")

            if agent.knowledge_base:
                prompt_parts.append(f"# Knowledge Base\n{agent.knowledge_base}")

            full_prompt = "\n\n".join(prompt_parts) if prompt_parts else ""

            # Build greeting
            greeting_message = agent.greeting_message or ""
            if greeting_message and customer_name:
                greeting_message = process_greeting(
                    template=greeting_message,
                    customer_data={
                        "customer_name": customer_name,
                        "customer_title": customer_title,
                    },
                    agent_name=getattr(agent, "name", "AI Agent"),
                    custom_variables=variables or {},
                )

            # Resolve language
            language = agent.language or "tr"

            # Resolve cloud pipeline provider settings (per-agent)
            stt_provider = getattr(agent, "stt_provider", None) or "deepgram"
            llm_provider = getattr(agent, "llm_provider", None) or "groq"
            tts_provider = getattr(agent, "tts_provider", None) or "cartesia"
            stt_model = getattr(agent, "stt_model", None) or ""
            llm_model = getattr(agent, "llm_model", None) or ""
            tts_model = getattr(agent, "tts_model", None) or ""
            tts_voice = getattr(agent, "tts_voice", None) or getattr(agent, "pipeline_voice", None) or getattr(agent, "voice", None) or ""

            call_setup_data = {
                "agent_id": str(agent.id),
                "agent_name": agent.name or "AI Agent",
                "name": agent.name or "AI Agent",
                "language": language,
                "prompt": full_prompt,
                "customer_name": customer_name or "",
                "customer_title": customer_title or "",
                "greeting_message": greeting_message,
                "first_speaker": agent.first_speaker or "agent",
                "max_duration": agent.max_duration or 300,
                "temperature": agent.temperature or 0.7,
                "conversation_history": conversation_history,
                "timezone": getattr(agent, "timezone", None) or "Europe/Istanbul",
                "provider": "pipeline",
                # Prompt sections for build_system_prompt()
                "prompt_role": getattr(agent, "prompt_role", None) or "",
                "prompt_personality": getattr(agent, "prompt_personality", None) or "",
                "prompt_context": getattr(agent, "prompt_context", None) or "",
                "prompt_pronunciations": getattr(agent, "prompt_pronunciations", None) or "",
                "prompt_sample_phrases": getattr(agent, "prompt_sample_phrases", None) or "",
                "prompt_tools": getattr(agent, "prompt_tools", None) or "",
                "prompt_rules": getattr(agent, "prompt_rules", None) or "",
                "prompt_flow": getattr(agent, "prompt_flow", None) or "",
                "prompt_safety": getattr(agent, "prompt_safety", None) or "",
                "prompt_language": getattr(agent, "prompt_language", None) or "",
                "knowledge_base": getattr(agent, "knowledge_base", None) or "",
                # Cloud pipeline providers (per-agent)
                "stt_provider": stt_provider,
                "llm_provider": llm_provider,
                "tts_provider": tts_provider,
                "stt_model": stt_model,
                "llm_model": llm_model,
                "tts_model": tts_model,
                "tts_voice": tts_voice,
            }

            if redis_client:
                try:
                    redis_client.setex(
                        f"call_setup:{call_uuid}",
                        900,  # 15 minutes TTL
                        json.dumps(call_setup_data),
                    )
                except Exception as e:
                    logger.error(f"Redis store error: {e}")

            channel_variables["VOICEAI_AGENT_ID"] = str(agent.id)
            channel_variables["VOICEAI_AGENT_NAME"] = agent.name or "AI Agent"

        if customer_name:
            channel_variables["VOICEAI_CUSTOMER_NAME"] = customer_name
        if customer_title:
            channel_variables["VOICEAI_CUSTOMER_TITLE"] = customer_title
        if variables:
            channel_variables.update(variables)

        # Call Asterisk ARI — use 'ai-outbound-pipeline' context
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels"
        data = {
            "endpoint": f"PJSIP/{phone_number}@trunk",
            "extension": "s",
            "context": "ai-outbound-pipeline",
            "callerId": f'"VoiceAI" <{caller_id}>',
            "timeout": 60,
        }
        if channel_variables:
            data["variables"] = channel_variables

        try:
            auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
            async with aiohttp.ClientSession() as session:
                async with session.post(ari_url, json=data, auth=auth) as response:
                    if response.status in (200, 201):
                        result = await response.json()
                        channel_id = result.get("id", "")
                        logger.info(
                            f"Pipeline call initiated: uuid={call_uuid[:8]}, "
                            f"channel={channel_id[:12] if channel_id else 'N/A'}, "
                            f"to={phone_number}, stt={stt_provider}, llm={llm_provider}, tts={tts_provider}"
                        )
                        return {
                            "call_id": call_uuid,
                            "ultravox_call_id": None,
                            "channel_id": channel_id,
                            "status": "ringing",
                        }
                    else:
                        error = await response.text()
                        logger.error(f"ARI originate error {response.status}: {error}")
                        raise Exception(f"Failed to originate call: {error}")

        except aiohttp.ClientError as e:
            logger.error(f"ARI connection error: {e}")
            raise

    async def end_call(self, call_id: str) -> dict:
        """End an active pipeline call via Asterisk ARI."""
        # Try to find channel from Redis
        channel_id = None
        if redis_client:
            try:
                channel_id = redis_client.get(f"call_channel:{call_id}")
            except Exception:
                pass

        if channel_id:
            # Hangup via ARI
            try:
                ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels/{channel_id}"
                auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
                async with aiohttp.ClientSession() as session:
                    async with session.delete(ari_url, auth=auth) as response:
                        if response.status in (200, 204, 404):
                            return {"success": True, "message": "Call ended"}
                        else:
                            error = await response.text()
                            logger.warning(f"ARI hangup error: {error}")
            except Exception as e:
                logger.error(f"ARI hangup error: {e}")

        return {"success": True, "message": "Call end requested"}

    async def get_transcript(self, call_id: str) -> list:
        """Get call transcript from Redis."""
        if not redis_client:
            return []

        try:
            transcript_key = f"call_transcript:{call_id}"
            messages = redis_client.lrange(transcript_key, 0, -1)
            transcript = []
            for msg_str in reversed(messages):  # LPUSH stores newest first
                try:
                    msg = json.loads(msg_str)
                    transcript.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                        "timestamp": msg.get("timestamp", ""),
                    })
                except json.JSONDecodeError:
                    continue
            return transcript
        except Exception as e:
            logger.error(f"Transcript fetch error: {e}")
            return []

    async def get_recording_url(self, call_id: str) -> Optional[str]:
        """Get recording URL — recordings handled by Asterisk."""
        # Pipeline calls are recorded by Asterisk if configured
        return None

    def calculate_cost(self, duration_seconds: int, **kwargs) -> dict:
        """Calculate cost — cloud pipeline has per-minute API costs."""
        import math
        duration_minutes = math.ceil(duration_seconds / 60)
        total_cost = round(duration_minutes * PIPELINE_RATE_PER_MINUTE, 4)
        return {
            "provider": "pipeline",
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_minutes,
            "rate_per_minute": PIPELINE_RATE_PER_MINUTE,
            "total_cost_usd": total_cost,
            "note": "Cloud pipeline - estimated cost (STT + LLM + TTS)",
        }
