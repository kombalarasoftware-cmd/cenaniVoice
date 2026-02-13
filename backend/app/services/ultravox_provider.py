"""
Ultravox call provider implementation.

Implements the CallProvider interface using Ultravox REST API
with native SIP support. No Asterisk or audio bridge needed.
"""

import json
import logging
import uuid as uuid_lib
from typing import Any, Optional

import redis

from app.core.config import settings
from app.services.call_provider import CallProvider
from app.services.ultravox_service import UltravoxService
from app.services.greeting_processor import process_greeting

logger = logging.getLogger(__name__)

# Redis client for call tracking
try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

# Ultravox pricing: $0.05 per minute
ULTRAVOX_RATE_PER_MINUTE = 0.05

# Voice mapping: OpenAI voice names → Ultravox voice names (from centralized config)
from app.core.voice_config import OPENAI_TO_ULTRAVOX_VOICE_MAP as VOICE_MAP

# Ultravox model mapping: internal model names → Ultravox API model values
ULTRAVOX_MODEL_MAP = {
    "ultravox-v0.7": "ultravox-v0.7",
    "ultravox-v0.6": "ultravox-v0.6",
    "ultravox-v0.6-gemma3-27b": "ultravox-v0.6-gemma3-27b",
    "ultravox-v0.6-llama3.3-70b": "ultravox-v0.6-llama3.3-70b",
    "ULTRAVOX_V0_6": "ultravox-v0.6",
    "ULTRAVOX_V0_6_GEMMA3_27B": "ultravox-v0.6-gemma3-27b",
    "ULTRAVOX_V0_6_LLAMA3_3_70B": "ultravox-v0.6-llama3.3-70b",
    "GPT_REALTIME_MINI": "ultravox-v0.7",
    "gpt-realtime-mini": "ultravox-v0.7",
    "gpt-realtime": "ultravox-v0.7",
}

# Prompt builder (centralized prompt construction)
from app.services.prompt_builder import PromptBuilder, PromptContext


class UltravoxProvider(CallProvider):
    """Call provider using Ultravox API with native SIP."""

    def __init__(self):
        self.service = UltravoxService()

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
        """Create an outbound call via Ultravox SIP."""
        call_uuid = str(uuid_lib.uuid4())

        # Build the full system prompt
        system_prompt = self._build_system_prompt(
            agent, customer_name, customer_title, conversation_history
        )

        # Map voice
        voice = self._map_voice(getattr(agent, "voice", "alloy"))

        # Map model - resolve to Ultravox API model name
        agent_model = getattr(agent, "model_type", None)
        if agent_model:
            model_value = agent_model.value if hasattr(agent_model, "value") else str(agent_model)
        else:
            model_value = "ultravox-v0.7"
        model = ULTRAVOX_MODEL_MAP.get(model_value, "ultravox-v0.7")

        # Build tools
        tools = self._build_ultravox_tools(agent)

        # Build VAD settings
        vad_settings = self._build_vad_settings(agent)

        # First speaker
        first_speaker = getattr(agent, "first_speaker", "agent") or "agent"

        # Language
        language = getattr(agent, "language", "en") or "en"

        # Temperature
        temperature = getattr(agent, "temperature", 0.3) or 0.3

        # Max duration
        max_duration_sec = getattr(agent, "max_duration", 300) or 300
        max_duration = f"{max_duration_sec}s"

        # Recording
        record_calls = getattr(agent, "record_calls", True)
        if record_calls is None:
            record_calls = True

        # Build greeting text for firstSpeakerSettings
        greeting_text = None
        greeting_message = getattr(agent, "greeting_message", "") or ""
        if greeting_message and first_speaker == "agent":
            # Process greeting template variables with language-aware titles
            customer_data_dict = {
                "name": customer_name,
                "customer_title": customer_title,  # Raw "Mr"/"Mrs" — translated by process_greeting
                "custom_data": (variables or {}).get("customer_data", {}),
            }
            greeting_text = process_greeting(
                template=greeting_message,
                customer_data=customer_data_dict,
                agent_name=getattr(agent, "name", "AI Agent"),
                language=language,
            )

        # SIP routing: Ultravox → Asterisk → SIP trunk
        # Ultravox registers as SIP endpoint on Asterisk.
        # Asterisk [from-ultravox] context routes the call through the SIP trunk.
        # This lets us cancel ringing calls via ARI channel DELETE → SIP CANCEL.
        sip_trunk_host = settings.ASTERISK_EXTERNAL_HOST
        sip_trunk_port = settings.ASTERISK_SIP_PORT or 5043
        sip_username = settings.ULTRAVOX_SIP_USERNAME
        sip_password = settings.ULTRAVOX_SIP_PASSWORD
        # CallerID: passed via SIP From header for logging;
        # Asterisk dialplan overrides with VOICEAI_CALLERID.
        sip_from = caller_id or settings.SIP_TRUNK_CALLER_ID

        if not sip_trunk_host:
            raise ValueError("ASTERISK_EXTERNAL_HOST must be configured for Ultravox SIP routing")

        # Build time exceeded message (spoken before hanging up at max duration)
        language = getattr(agent, "language", "en") or "en"
        time_exceeded_messages = {
            "tr": "Görüşme süremiz doldu. Yardımcı olabildiysem ne mutlu, iyi günler.",
            "en": "I'm afraid we've reached our time limit. Thank you for your time, goodbye.",
            "de": "Unsere Gesprächszeit ist leider abgelaufen. Vielen Dank für Ihre Zeit, auf Wiedersehen.",
            "fr": "Je suis désolé, notre temps de conversation est écoulé. Merci pour votre temps, au revoir.",
            "es": "Lo siento, nuestro tiempo de conversación ha terminado. Gracias por su tiempo, adiós.",
        }
        time_exceeded_msg = time_exceeded_messages.get(language, time_exceeded_messages["en"])

        try:
            result = await self.service.create_call(
                system_prompt=system_prompt,
                voice=voice,
                model=model,
                temperature=temperature,
                sip_to=phone_number,
                sip_from=sip_from,
                sip_username=sip_username,
                sip_password=sip_password,
                sip_trunk_host=sip_trunk_host,
                sip_trunk_port=sip_trunk_port,
                tools=tools,
                first_speaker=first_speaker,
                recording_enabled=record_calls,
                max_duration=max_duration,
                language_hint=language,
                vad_settings=vad_settings,
                greeting_text=greeting_text,
                time_exceeded_message=time_exceeded_msg,
            )

            ultravox_call_id = result.get("callId", "")

            # Store mapping in Redis for webhook correlation (non-fatal)
            if redis_client and ultravox_call_id:
                try:
                    mapping = {
                        "call_uuid": call_uuid,
                        "ultravox_call_id": ultravox_call_id,
                        "agent_id": str(getattr(agent, "id", "")),
                        "phone_number": phone_number,
                        "customer_name": customer_name,
                        "campaign_id": str(campaign_id) if campaign_id else "",
                    }
                    redis_client.setex(
                        f"ultravox_call:{ultravox_call_id}",
                        7200,  # 2 hour TTL for safety margin
                        json.dumps(mapping),
                    )
                    # Reverse mapping
                    redis_client.setex(
                        f"call_ultravox:{call_uuid}",
                        7200,  # 2 hour TTL
                        ultravox_call_id,
                    )
                except Exception as redis_err:
                    logger.warning(f"Redis mapping store failed (non-fatal): {redis_err}")

            logger.info(
                f"Ultravox call created: uuid={call_uuid[:8]}, "
                f"ultravox_id={ultravox_call_id[:8] if ultravox_call_id else 'N/A'}, "
                f"to={phone_number}"
            )

            return {
                "call_id": call_uuid,
                "ultravox_call_id": ultravox_call_id,
                "channel_id": None,  # No Asterisk channel
                "status": "ringing",
            }

        except Exception as e:
            logger.error(f"Ultravox call creation failed: {e}")
            raise

    async def end_call(self, call_id: str) -> dict:
        """End an active Ultravox call."""
        # Resolve Ultravox call ID from our UUID
        ultravox_call_id = call_id
        if redis_client:
            mapped_id = redis_client.get(f"call_ultravox:{call_id}")
            if mapped_id:
                ultravox_call_id = mapped_id

        try:
            result = await self.service.end_call(ultravox_call_id)
            if result.get("joined"):
                return result
            # 422: call was still ringing — DELETE to cancel SIP leg
            logger.info(f"Ultravox call not joined, deleting to cancel SIP")
            try:
                return await self.service.delete_call(ultravox_call_id)
            except Exception:
                return result  # Return original result if DELETE also fails
        except Exception as e:
            logger.warning(f"Ultravox end_call failed, trying DELETE: {e}")
            try:
                return await self.service.delete_call(ultravox_call_id)
            except Exception as e2:
                logger.error(f"Ultravox DELETE also failed: {e2}")
                return {"success": False, "message": "Failed to end call"}

    async def get_transcript(self, call_id: str) -> list:
        """Get call transcript from Ultravox API."""
        ultravox_call_id = call_id
        if redis_client:
            mapped_id = redis_client.get(f"call_ultravox:{call_id}")
            if mapped_id:
                ultravox_call_id = mapped_id

        try:
            messages = await self.service.get_call_messages(ultravox_call_id)
            # Normalize to app format
            transcript = []
            for msg in messages:
                role = msg.get("role", "")
                if role == "agent":
                    role = "assistant"
                transcript.append({
                    "role": role,
                    "content": msg.get("text", ""),
                    "timestamp": msg.get("timestamp", ""),
                })
            return transcript
        except Exception as e:
            logger.error(f"Ultravox get_transcript failed: {e}")
            return []

    async def get_recording_url(self, call_id: str) -> Optional[str]:
        """Get recording URL from Ultravox API."""
        ultravox_call_id = call_id
        if redis_client:
            mapped_id = redis_client.get(f"call_ultravox:{call_id}")
            if mapped_id:
                ultravox_call_id = mapped_id

        return await self.service.get_call_recording(ultravox_call_id)

    def calculate_cost(self, duration_seconds: int, **kwargs) -> dict:
        """Calculate cost based on Ultravox per-deciminute pricing.

        Ultravox rounds up to the nearest 'deciminute' (6-second increment).
        E.g. 3s → 6s, 37s → 42s, 55s → 60s.
        Rate: $0.005 per 6 seconds ($0.05 per minute).
        """
        import math
        deciminutes = math.ceil(duration_seconds / 6)  # round up to nearest 6s
        billed_seconds = deciminutes * 6
        billed_minutes = billed_seconds / 60
        total = round(deciminutes * 0.005, 4)  # $0.005 per 6-second increment
        return {
            "provider": "ultravox",
            "duration_seconds": duration_seconds,
            "billed_seconds": billed_seconds,
            "duration_minutes": round(billed_minutes, 2),
            "rate_per_minute": ULTRAVOX_RATE_PER_MINUTE,
            "total_cost_usd": total,
        }

    # ---------------------------------------------------------------- Private

    def _build_system_prompt(
        self,
        agent: Any,
        customer_name: str = "",
        customer_title: str = "",
        conversation_history: str = "",
    ) -> str:
        """Build system prompt using the universal PromptBuilder.

        Delegates to PromptBuilder which handles all 4 layers:
        1. Agent DB sections (10 fields)
        2. Universal dynamic (date/time, voice rules, safety, instruction tags)
        3. Contextual (customer context, conversation history)
        4. Provider-specific (full AMD for Ultravox)
        """
        ctx = PromptContext.from_agent(
            agent,
            customer_name=customer_name,
            customer_title=customer_title,
            conversation_history=conversation_history,
        )
        return PromptBuilder.build(ctx)

    def _map_voice(self, openai_voice: str) -> str:
        """Map OpenAI voice name to Ultravox voice name."""
        return VOICE_MAP.get(openai_voice, openai_voice)

    def _build_vad_settings(self, agent: Any) -> dict:
        """Build Ultravox VAD settings from agent config."""
        silence_ms = getattr(agent, "silence_duration_ms", 800) or 800
        vad_threshold = getattr(agent, "vad_threshold", 0.1) or 0.1
        eagerness = getattr(agent, "vad_eagerness", "low") or "low"

        # Map eagerness to minimum interruption duration
        interruption_map = {
            "low": "0.3s",
            "medium": "0.15s",
            "high": "0.05s",
            "auto": "0.09s",
        }

        return {
            "turnEndpointDelay": f"{silence_ms / 1000:.3f}s",
            "minimumTurnDuration": "0s",
            "minimumInterruptionDuration": interruption_map.get(eagerness, "0.09s"),
            "frameActivationThreshold": vad_threshold,
        }

    def _build_ultravox_tools(self, agent: Any) -> list:
        """
        Build Ultravox HTTP tool definitions from universal tool registry.

        Uses the central tool_registry so that ALL tools are
        consistently available regardless of provider.
        NOTE: Ultravox requires HTTPS URLs for HTTP tools.
        If no public HTTPS URL is configured, only built-in tools are returned.
        """
        from app.services.tool_registry import to_ultravox_tools

        webhook_base = settings.ULTRAVOX_WEBHOOK_URL
        if not webhook_base or not webhook_base.startswith("https://"):
            logger.warning(
                "ULTRAVOX_WEBHOOK_URL is not HTTPS — skipping HTTP tools. "
                "Set a public HTTPS URL to enable tools."
            )
            # Return only built-in tools that don't need HTTP
            tools = [{"toolName": "hangUp"}]
            return tools

        # Normalize: webhook URL should point to tools base
        if webhook_base.endswith("/ultravox"):
            webhook_base = webhook_base.replace("/webhooks/ultravox", "/tools")
        elif not webhook_base.endswith("/tools"):
            webhook_base = webhook_base.rstrip("/") + "/api/v1/tools"

        # Build agent_config dict from agent model for tool filtering
        agent_config = {
            "human_transfer": getattr(agent, "human_transfer", True),
            "survey_config": getattr(agent, "survey_config", None),
        }

        return to_ultravox_tools(agent_config, webhook_base)
