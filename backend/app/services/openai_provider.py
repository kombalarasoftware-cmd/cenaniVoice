"""
OpenAI Realtime call provider implementation.

Wraps the existing Asterisk + AudioSocket + OpenAI Realtime flow
behind the CallProvider interface. This provider delegates to
the existing asterisk_bridge.py without any changes to it.
"""

import json
import logging
import os
import uuid as uuid_lib
from typing import Any, Optional

import aiohttp
import redis

from app.core.config import settings
from app.services.call_provider import CallProvider

logger = logging.getLogger(__name__)

# Redis client for call setup and transcripts
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

# Asterisk ARI config
ARI_HOST = os.environ.get("ASTERISK_HOST", "asterisk")
ARI_PORT = int(os.environ.get("ASTERISK_ARI_PORT", "8088"))
ARI_USERNAME = os.environ.get("ASTERISK_ARI_USER", "voiceai")
ARI_PASSWORD = os.environ.get("ASTERISK_ARI_PASSWORD", "voiceai_ari_secret")

# OpenAI Realtime pricing (per 1M tokens)
COST_PER_TOKEN = {
    "gpt-realtime": {
        "input_text": 4.00 / 1_000_000,
        "input_audio": 32.00 / 1_000_000,
        "cached_input_text": 0.40 / 1_000_000,
        "cached_input_audio": 0.40 / 1_000_000,
        "output_text": 16.00 / 1_000_000,
        "output_audio": 64.00 / 1_000_000,
    },
    "gpt-realtime-mini": {
        "input_text": 0.60 / 1_000_000,
        "input_audio": 10.00 / 1_000_000,
        "cached_input_text": 0.06 / 1_000_000,
        "cached_input_audio": 0.30 / 1_000_000,
        "output_text": 2.40 / 1_000_000,
        "output_audio": 20.00 / 1_000_000,
    },
}

VALID_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse", "marin", "cedar"}


class OpenAIProvider(CallProvider):
    """
    Call provider using Asterisk + AudioSocket + OpenAI Realtime.

    This wraps the existing outbound call flow:
    1. Store agent config in Redis
    2. Call Asterisk ARI to originate channel
    3. asterisk_bridge.py handles the audio bridging
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
        """Initiate call via Asterisk ARI (existing flow)."""
        call_uuid = str(uuid_lib.uuid4())

        channel_variables = {
            "VOICEAI_UUID": call_uuid,
        }

        # Build agent config for the bridge
        if agent:
            model_str = str(agent.model_type) if agent.model_type else "gpt-realtime-mini"
            if "RealtimeModel." in model_str:
                model_str = model_str.replace(
                    "RealtimeModel.GPT_REALTIME_MINI", "gpt-realtime-mini"
                ).replace("RealtimeModel.GPT_REALTIME", "gpt-realtime")

            # Build prompt from sections
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
                ("Guardrails", "prompt_safety"),
                ("Language", "prompt_language"),
            ]
            for heading, attr in section_map:
                content = getattr(agent, attr, None)
                if content:
                    prompt_parts.append(f"# {heading}\n{content}")

            if agent.knowledge_base:
                prompt_parts.append(f"# Knowledge Base\n{agent.knowledge_base}")

            full_prompt = "\n\n".join(prompt_parts) if prompt_parts else ""

            agent_voice = agent.voice if agent.voice in VALID_VOICES else "ash"

            call_setup_data = {
                "agent_id": str(agent.id),
                "agent_name": agent.name or "AI Agent",
                "voice": agent_voice,
                "model": model_str,
                "language": agent.language or "tr",
                "prompt": full_prompt,
                "customer_name": customer_name or "",
                "customer_title": customer_title or "",
                "greeting_message": agent.greeting_message or "",
                "first_speaker": agent.first_speaker or "agent",
                "greeting_uninterruptible": agent.greeting_uninterruptible or False,
                "first_message_delay": agent.first_message_delay or 0.0,
                "max_duration": agent.max_duration or 300,
                "silence_timeout": agent.silence_timeout or 10,
                "temperature": agent.temperature or 0.7,
                "vad_threshold": agent.vad_threshold or 0.5,
                "turn_detection": agent.turn_detection or "semantic_vad",
                "vad_eagerness": agent.vad_eagerness or "low",
                "silence_duration_ms": agent.silence_duration_ms or 1000,
                "prefix_padding_ms": agent.prefix_padding_ms or 400,
                "interrupt_response": agent.interrupt_response if agent.interrupt_response is not None else True,
                "create_response": agent.create_response if agent.create_response is not None else True,
                "noise_reduction": agent.noise_reduction if agent.noise_reduction is not None else True,
                "max_output_tokens": agent.max_output_tokens or 500,
                "speech_speed": agent.speech_speed or 1.0,
                "idle_timeout_ms": agent.idle_timeout_ms,
                "transcript_model": getattr(agent, "transcript_model", None) or "gpt-4o-transcribe",
                "inactivity_messages": agent.inactivity_messages or [],
                "interruptible": agent.interruptible if agent.interruptible is not None else True,
                "record_calls": agent.record_calls if agent.record_calls is not None else True,
                "human_transfer": agent.human_transfer if agent.human_transfer is not None else True,
                "conversation_history": conversation_history,
            }

            if redis_client:
                try:
                    redis_client.setex(
                        f"call_setup:{call_uuid}",
                        300,
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

        # Call Asterisk ARI
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels"
        data = {
            "endpoint": f"PJSIP/{phone_number}@trunk",
            "extension": "s",
            "context": "ai-outbound",
            "callerId": f'"VoiceAI" <{caller_id}>',
            "timeout": 60,
        }
        if channel_variables:
            data["variables"] = channel_variables

        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.post(ari_url, json=data) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise RuntimeError(f"ARI error: {response.status} - {error_text}")

                result = await response.json()
                channel_id = result.get("id")

        logger.info(f"OpenAI call initiated: uuid={call_uuid[:8]}, channel={channel_id}")

        return {
            "call_id": call_uuid,
            "ultravox_call_id": None,
            "channel_id": channel_id,
            "status": "ringing",
        }

    async def end_call(self, call_id: str) -> dict:
        """End call via Redis signal and ARI hangup."""
        results = []

        # Send Redis hangup signal
        if redis_client:
            try:
                redis_client.setex(f"hangup_signal:{call_id}", 60, "1")
                results.append("Redis hangup signal sent")
            except Exception as e:
                logger.warning(f"Redis hangup signal error: {e}")

        return {"success": True, "message": "; ".join(results) if results else "Hangup signal sent"}

    async def get_transcript(self, call_id: str) -> list:
        """Get transcript from Redis (stored by asterisk_bridge)."""
        if not redis_client:
            return []

        try:
            transcript_key = f"call_transcript:{call_id}"
            raw = redis_client.lrange(transcript_key, 0, -1)
            transcript = []
            for item in reversed(raw):  # LPUSH stores in reverse
                try:
                    entry = json.loads(item)
                    transcript.append({
                        "role": entry.get("role", ""),
                        "content": entry.get("content", ""),
                        "timestamp": entry.get("timestamp", ""),
                    })
                except (json.JSONDecodeError, TypeError):
                    pass
            return transcript
        except Exception as e:
            logger.error(f"Error reading transcript from Redis: {e}")
            return []

    async def get_recording_url(self, call_id: str) -> Optional[str]:
        """Get recording URL (stored in DB by bridge post-call processing)."""
        return None  # Recording URL is set in CallLog by the bridge

    def calculate_cost(self, duration_seconds: int, **kwargs) -> dict:
        """Calculate cost based on OpenAI token pricing."""
        model = kwargs.get("model", "gpt-realtime-mini")
        input_tokens = kwargs.get("input_tokens", 0)
        output_tokens = kwargs.get("output_tokens", 0)
        cached_tokens = kwargs.get("cached_tokens", 0)

        pricing = COST_PER_TOKEN.get(model, COST_PER_TOKEN["gpt-realtime-mini"])

        input_cost = input_tokens * pricing["input_audio"]
        output_cost = output_tokens * pricing["output_audio"]
        cached_cost = cached_tokens * pricing["cached_input_audio"]
        total = round(input_cost + output_cost + cached_cost, 6)

        return {
            "provider": "openai",
            "duration_seconds": duration_seconds,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "total_cost_usd": total,
        }
