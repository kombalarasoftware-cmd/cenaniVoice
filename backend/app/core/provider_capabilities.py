"""
Provider capabilities configuration.

Defines which settings each AI provider supports.
Used by the /providers/capabilities endpoint and provider services.
"""

from typing import Any


# Provider capability map — authoritative source of truth
# Each setting has: supported (bool), label for UI, description, and optionally constraints
PROVIDER_CAPABILITIES: dict[str, dict[str, Any]] = {
    "openai": {
        "label": "OpenAI Realtime",
        "description": "GPT-4o Realtime via Asterisk bridge",
        "settings": {
            # Voice & Basic
            "temperature": True,
            "max_duration": True,
            "record_calls": True,
            "auto_transcribe": True,
            "human_transfer": True,
            # Advanced — VAD / Turn Detection
            "turn_detection": True,
            "vad_threshold": True,
            "vad_eagerness": True,
            "silence_duration_ms": True,
            "prefix_padding_ms": True,
            "create_response": True,
            # Advanced — Model behavior
            "max_output_tokens": True,
            "noise_reduction": True,
            "transcript_model": True,
            # Greeting
            "greeting_uninterruptible": True,
            "first_message_delay": True,
            # Ultravox-specific call settings
            "initial_output_medium": False,
            "join_timeout": False,
            "time_exceeded_message": False,
        },
    },
    "xai": {
        "label": "xAI Grok",
        "description": "Grok voice agent with per-minute billing",
        "settings": {
            # Voice & Basic
            "temperature": False,
            "max_duration": True,
            "record_calls": True,
            "auto_transcribe": False,
            "human_transfer": True,
            # Advanced — VAD / Turn Detection
            "turn_detection": False,
            "vad_threshold": False,
            "vad_eagerness": False,
            "silence_duration_ms": False,
            "prefix_padding_ms": False,
            "create_response": False,
            # Advanced — Model behavior
            "max_output_tokens": False,
            "noise_reduction": False,
            "transcript_model": False,
            # Greeting
            "greeting_uninterruptible": True,
            "first_message_delay": True,
            # Ultravox-specific call settings
            "initial_output_medium": False,
            "join_timeout": False,
            "time_exceeded_message": False,
        },
    },
    "gemini": {
        "label": "Google Gemini",
        "description": "Gemini Live via Vertex AI with native audio",
        "settings": {
            # Voice & Basic
            "temperature": True,
            "max_duration": True,
            "record_calls": True,
            "auto_transcribe": False,
            "human_transfer": True,
            # Advanced — VAD / Turn Detection
            "turn_detection": False,
            "vad_threshold": False,
            "vad_eagerness": False,
            "silence_duration_ms": False,
            "prefix_padding_ms": False,
            "create_response": False,
            # Advanced — Model behavior
            "max_output_tokens": False,
            "noise_reduction": False,
            "transcript_model": False,
            # Greeting
            "greeting_uninterruptible": True,
            "first_message_delay": True,
            # Ultravox-specific call settings
            "initial_output_medium": False,
            "join_timeout": False,
            "time_exceeded_message": False,
        },
    },
    "ultravox": {
        "label": "Ultravox",
        "description": "Native SIP with built-in VAD and transcription",
        "settings": {
            # Voice & Basic
            "temperature": True,
            "max_duration": True,
            "record_calls": True,
            "auto_transcribe": False,
            "human_transfer": True,
            # Advanced — VAD / Turn Detection
            "turn_detection": False,
            "vad_threshold": True,
            "vad_eagerness": True,
            "silence_duration_ms": True,
            "prefix_padding_ms": False,
            "create_response": False,
            # Advanced — Model behavior
            "max_output_tokens": False,
            "noise_reduction": False,
            "transcript_model": False,
            # Greeting
            "greeting_uninterruptible": False,
            "first_message_delay": False,
            # Ultravox-specific call settings
            "initial_output_medium": True,
            "join_timeout": True,
            "time_exceeded_message": True,
        },
    },
}


def get_provider_capabilities(provider: str) -> dict[str, Any] | None:
    """Return capabilities for a given provider name."""
    return PROVIDER_CAPABILITIES.get(provider)


def get_all_capabilities() -> dict[str, dict[str, Any]]:
    """Return capabilities for all providers."""
    return PROVIDER_CAPABILITIES
