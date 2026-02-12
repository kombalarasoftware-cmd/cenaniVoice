"""
Centralized voice configuration for all providers.
Single source of truth for voice definitions, gender, and provider compatibility.
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class VoiceGender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class VoiceDefinition:
    id: str
    name: str
    gender: VoiceGender
    description: str
    provider: str  # "openai", "ultravox", "xai", or "gemini"
    language: Optional[str] = None  # None means multilingual (OpenAI)
    recommended: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender.value,
            "description": self.description,
            "provider": self.provider,
            "language": self.language,
            "recommended": self.recommended,
        }


# =============================================================================
# OpenAI Realtime API Voices
# Supported by: gpt-realtime, gpt-realtime-mini
# Source: https://developers.openai.com/api/docs/guides/realtime-conversations
# =============================================================================
OPENAI_REALTIME_VOICES: List[VoiceDefinition] = [
    VoiceDefinition("alloy", "Alloy", VoiceGender.FEMALE, "Neutral, balanced tone", "openai"),
    VoiceDefinition("ash", "Ash", VoiceGender.MALE, "Confident, clear male", "openai"),
    VoiceDefinition("ballad", "Ballad", VoiceGender.MALE, "Warm, deep male", "openai"),
    VoiceDefinition("coral", "Coral", VoiceGender.FEMALE, "Friendly, warm female", "openai"),
    VoiceDefinition("echo", "Echo", VoiceGender.MALE, "Deep, resonant male", "openai"),
    VoiceDefinition("sage", "Sage", VoiceGender.FEMALE, "Calm, wise female", "openai"),
    VoiceDefinition("shimmer", "Shimmer", VoiceGender.FEMALE, "Soft, gentle female", "openai"),
    VoiceDefinition("verse", "Verse", VoiceGender.MALE, "Dynamic, expressive male", "openai"),
    VoiceDefinition("marin", "Marin", VoiceGender.FEMALE, "Natural, recommended female", "openai", recommended=True),
    VoiceDefinition("cedar", "Cedar", VoiceGender.MALE, "Natural, recommended male", "openai", recommended=True),
]

# Valid voice IDs for quick validation
OPENAI_VALID_VOICES = {v.id for v in OPENAI_REALTIME_VOICES}

# Voice ID to definition mapping
OPENAI_VOICE_MAP: Dict[str, VoiceDefinition] = {v.id: v for v in OPENAI_REALTIME_VOICES}


# =============================================================================
# Ultravox Voices
# Maps to Ultravox built-in voice names
# =============================================================================
ULTRAVOX_VOICES: List[VoiceDefinition] = [
    # Turkish
    VoiceDefinition("Cicek-Turkish", "Cicek", VoiceGender.FEMALE, "Turkish female", "ultravox", "tr"),
    VoiceDefinition("Doga-Turkish", "Doga", VoiceGender.MALE, "Turkish male", "ultravox", "tr"),
    # English
    VoiceDefinition("Mark", "Mark", VoiceGender.MALE, "English male", "ultravox", "en"),
    VoiceDefinition("Jessica", "Jessica", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Sarah", "Sarah", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Alex", "Alex", VoiceGender.MALE, "English male", "ultravox", "en"),
    VoiceDefinition("Carter", "Carter", VoiceGender.MALE, "English male (Cartesia)", "ultravox", "en"),
    VoiceDefinition("Olivia", "Olivia", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Edward", "Edward", VoiceGender.MALE, "English male", "ultravox", "en"),
    VoiceDefinition("Luna", "Luna", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Ashley", "Ashley", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Dennis", "Dennis", VoiceGender.MALE, "English male", "ultravox", "en"),
    VoiceDefinition("Theodore", "Theodore", VoiceGender.MALE, "English male", "ultravox", "en"),
    VoiceDefinition("Julia", "Julia", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Shaun", "Shaun", VoiceGender.MALE, "English male", "ultravox", "en"),
    VoiceDefinition("Hana", "Hana", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Blake", "Blake", VoiceGender.MALE, "English male", "ultravox", "en"),
    VoiceDefinition("Timothy", "Timothy", VoiceGender.MALE, "English male", "ultravox", "en"),
    VoiceDefinition("Chelsea", "Chelsea", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Emily-English", "Emily", VoiceGender.FEMALE, "English female", "ultravox", "en"),
    VoiceDefinition("Aaron-English", "Aaron", VoiceGender.MALE, "English male", "ultravox", "en"),
    # German
    VoiceDefinition("Josef", "Josef", VoiceGender.MALE, "German male", "ultravox", "de"),
    VoiceDefinition("Johanna", "Johanna", VoiceGender.FEMALE, "German female", "ultravox", "de"),
    VoiceDefinition("Ben-German", "Ben", VoiceGender.MALE, "German male", "ultravox", "de"),
    VoiceDefinition("Susi-German", "Susi", VoiceGender.FEMALE, "German female", "ultravox", "de"),
    # French
    VoiceDefinition("Hugo-French", "Hugo", VoiceGender.MALE, "French male", "ultravox", "fr"),
    VoiceDefinition("Coco-French", "Coco", VoiceGender.FEMALE, "French female", "ultravox", "fr"),
    VoiceDefinition("Alize-French", "Alize", VoiceGender.FEMALE, "French female", "ultravox", "fr"),
    VoiceDefinition("Nicolas-French", "Nicolas", VoiceGender.MALE, "French male", "ultravox", "fr"),
    # Spanish
    VoiceDefinition("Alex-Spanish", "Alex", VoiceGender.MALE, "Spanish male", "ultravox", "es"),
    VoiceDefinition("Andrea-Spanish", "Andrea", VoiceGender.FEMALE, "Spanish female", "ultravox", "es"),
    VoiceDefinition("Tatiana-Spanish", "Tatiana", VoiceGender.FEMALE, "Spanish female", "ultravox", "es"),
    VoiceDefinition("Mauricio-Spanish", "Mauricio", VoiceGender.MALE, "Spanish male", "ultravox", "es"),
    # Italian
    VoiceDefinition("Linda-Italian", "Linda", VoiceGender.FEMALE, "Italian female", "ultravox", "it"),
    VoiceDefinition("Giovanni-Italian", "Giovanni", VoiceGender.MALE, "Italian male", "ultravox", "it"),
    # Portuguese
    VoiceDefinition("Rosa-Portuguese", "Rosa", VoiceGender.FEMALE, "Portuguese female", "ultravox", "pt"),
    VoiceDefinition("Tiago-Portuguese", "Tiago", VoiceGender.MALE, "Portuguese male", "ultravox", "pt"),
    # Arabic
    VoiceDefinition("Salma-Arabic", "Salma", VoiceGender.FEMALE, "Arabic female", "ultravox", "ar"),
    VoiceDefinition("Raed-Arabic", "Raed", VoiceGender.MALE, "Arabic male", "ultravox", "ar"),
    # Japanese
    VoiceDefinition("Morioki-Japanese", "Morioki", VoiceGender.MALE, "Japanese male", "ultravox", "ja"),
    VoiceDefinition("Asahi-Japanese", "Asahi", VoiceGender.FEMALE, "Japanese female", "ultravox", "ja"),
    # Korean
    VoiceDefinition("Yoona", "Yoona", VoiceGender.FEMALE, "Korean female", "ultravox", "ko"),
    VoiceDefinition("Seojun", "Seojun", VoiceGender.MALE, "Korean male", "ultravox", "ko"),
    # Chinese
    VoiceDefinition("Maya-Chinese", "Maya", VoiceGender.FEMALE, "Chinese female", "ultravox", "zh"),
    VoiceDefinition("Martin-Chinese", "Martin", VoiceGender.MALE, "Chinese male", "ultravox", "zh"),
    # Hindi
    VoiceDefinition("Riya-Hindi-Urdu", "Riya", VoiceGender.FEMALE, "Hindi female", "ultravox", "hi"),
    VoiceDefinition("Aakash-Hindi", "Aakash", VoiceGender.MALE, "Hindi male", "ultravox", "hi"),
    # Russian
    VoiceDefinition("Nadia-Russian", "Nadia", VoiceGender.FEMALE, "Russian female", "ultravox", "ru"),
    VoiceDefinition("Felix-Russian", "Felix", VoiceGender.MALE, "Russian male", "ultravox", "ru"),
    # Dutch
    VoiceDefinition("Ruth-Dutch", "Ruth", VoiceGender.FEMALE, "Dutch female", "ultravox", "nl"),
    VoiceDefinition("Daniel-Dutch", "Daniel", VoiceGender.MALE, "Dutch male", "ultravox", "nl"),
    # Ukrainian
    VoiceDefinition("Vira-Ukrainian", "Vira", VoiceGender.FEMALE, "Ukrainian female", "ultravox", "uk"),
    VoiceDefinition("Dmytro-Ukrainian", "Dmytro", VoiceGender.MALE, "Ukrainian male", "ultravox", "uk"),
    # Swedish
    VoiceDefinition("Sanna-Swedish", "Sanna", VoiceGender.FEMALE, "Swedish female", "ultravox", "sv"),
    VoiceDefinition("Adam-Swedish", "Adam", VoiceGender.MALE, "Swedish male", "ultravox", "sv"),
    # Polish
    VoiceDefinition("Hanna-Polish", "Hanna", VoiceGender.FEMALE, "Polish female", "ultravox", "pl"),
    VoiceDefinition("Marcin-Polish", "Marcin", VoiceGender.MALE, "Polish male", "ultravox", "pl"),
]

ULTRAVOX_VALID_VOICES = {v.id for v in ULTRAVOX_VOICES}


# =============================================================================
# xAI Grok Voice Agent Voices
# Source: https://docs.x.ai/developers/model-capabilities/audio/voice-agent
# =============================================================================
XAI_VOICES: List[VoiceDefinition] = [
    VoiceDefinition("Ara", "Ara", VoiceGender.FEMALE, "Warm, friendly - Default", "xai", recommended=True),
    VoiceDefinition("Rex", "Rex", VoiceGender.MALE, "Confident, clear", "xai"),
    VoiceDefinition("Sal", "Sal", VoiceGender.NEUTRAL, "Smooth, balanced - Neutral", "xai"),
    VoiceDefinition("Eve", "Eve", VoiceGender.FEMALE, "Energetic, upbeat", "xai"),
    VoiceDefinition("Leo", "Leo", VoiceGender.MALE, "Authoritative, strong", "xai"),
]

XAI_VALID_VOICES = {v.id for v in XAI_VOICES}


# =============================================================================
# Google Gemini Live Voices (Vertex AI)
# Source: https://ai.google.dev/gemini-api/docs/speech-generation
# 30 voices available, multilingual support (70+ languages)
# =============================================================================
GEMINI_VOICES: List[VoiceDefinition] = [
    # Recommended voices
    VoiceDefinition("Kore", "Kore", VoiceGender.FEMALE, "Firm - Default", "gemini", recommended=True),
    VoiceDefinition("Puck", "Puck", VoiceGender.MALE, "Upbeat", "gemini", recommended=True),
    # All 30 Gemini Live voices (official descriptions from Google docs)
    VoiceDefinition("Charon", "Charon", VoiceGender.MALE, "Informative", "gemini"),
    VoiceDefinition("Zephyr", "Zephyr", VoiceGender.FEMALE, "Bright", "gemini"),
    VoiceDefinition("Fenrir", "Fenrir", VoiceGender.MALE, "Excitable", "gemini"),
    VoiceDefinition("Leda", "Leda", VoiceGender.FEMALE, "Youthful", "gemini"),
    VoiceDefinition("Orus", "Orus", VoiceGender.MALE, "Firm", "gemini"),
    VoiceDefinition("Aoede", "Aoede", VoiceGender.FEMALE, "Breezy", "gemini"),
    VoiceDefinition("Autonoe", "Autonoe", VoiceGender.FEMALE, "Bright", "gemini"),
    VoiceDefinition("Callirrhoe", "Callirrhoe", VoiceGender.FEMALE, "Easy-going", "gemini"),
    VoiceDefinition("Enceladus", "Enceladus", VoiceGender.MALE, "Breathy", "gemini"),
    VoiceDefinition("Iapetus", "Iapetus", VoiceGender.MALE, "Clear", "gemini"),
    VoiceDefinition("Umbriel", "Umbriel", VoiceGender.NEUTRAL, "Easy-going", "gemini"),
    VoiceDefinition("Algieba", "Algieba", VoiceGender.MALE, "Smooth", "gemini"),
    VoiceDefinition("Despina", "Despina", VoiceGender.FEMALE, "Smooth", "gemini"),
    VoiceDefinition("Erinome", "Erinome", VoiceGender.FEMALE, "Clear", "gemini"),
    VoiceDefinition("Laomedeia", "Laomedeia", VoiceGender.FEMALE, "Upbeat", "gemini"),
    VoiceDefinition("Schedar", "Schedar", VoiceGender.FEMALE, "Even", "gemini"),
    VoiceDefinition("Achird", "Achird", VoiceGender.MALE, "Friendly", "gemini"),
    VoiceDefinition("Sadachbia", "Sadachbia", VoiceGender.MALE, "Lively", "gemini"),
    VoiceDefinition("Algenib", "Algenib", VoiceGender.MALE, "Gravelly", "gemini"),
    VoiceDefinition("Achernar", "Achernar", VoiceGender.FEMALE, "Soft", "gemini"),
    VoiceDefinition("Gacrux", "Gacrux", VoiceGender.MALE, "Mature", "gemini"),
    VoiceDefinition("Zubenelgenubi", "Zubenelgenubi", VoiceGender.MALE, "Casual", "gemini"),
    VoiceDefinition("Sadaltager", "Sadaltager", VoiceGender.MALE, "Knowledgeable", "gemini"),
    VoiceDefinition("Rasalgethi", "Rasalgethi", VoiceGender.MALE, "Informative", "gemini"),
    VoiceDefinition("Alnilam", "Alnilam", VoiceGender.MALE, "Firm", "gemini"),
    VoiceDefinition("Pulcherrima", "Pulcherrima", VoiceGender.FEMALE, "Forward", "gemini"),
    VoiceDefinition("Vindemiatrix", "Vindemiatrix", VoiceGender.FEMALE, "Gentle", "gemini"),
    VoiceDefinition("Sulafat", "Sulafat", VoiceGender.FEMALE, "Warm", "gemini"),
]

GEMINI_VALID_VOICES = {v.id for v in GEMINI_VOICES}

# OpenAI voice name → Ultravox voice name mapping
OPENAI_TO_ULTRAVOX_VOICE_MAP = {
    "alloy": "Alex",
    "ash": "Mark",
    "ballad": "Sarah",
    "coral": "Olivia",
    "echo": "Edward",
    "sage": "Jessica",
    "shimmer": "Luna",
    "verse": "Carter",
    "marin": "Dennis",
    "cedar": "Theodore",
    "fable": "Julia",
    "onyx": "Shaun",
    "nova": "Ashley",
}


def get_voices_by_provider(provider: str) -> List[dict]:
    """Get voice list for a specific provider."""
    if provider == "openai":
        return [v.to_dict() for v in OPENAI_REALTIME_VOICES]
    elif provider == "ultravox":
        return [v.to_dict() for v in ULTRAVOX_VOICES]
    elif provider == "xai":
        return [v.to_dict() for v in XAI_VOICES]
    elif provider == "gemini":
        return [v.to_dict() for v in GEMINI_VOICES]
    return []


def get_voices_by_gender(provider: str, gender: str) -> List[dict]:
    """Get voices filtered by provider and gender."""
    if provider == "xai":
        voices = XAI_VOICES
    elif provider == "ultravox":
        voices = ULTRAVOX_VOICES
    elif provider == "gemini":
        voices = GEMINI_VOICES
    else:
        voices = OPENAI_REALTIME_VOICES
    return [v.to_dict() for v in voices if v.gender.value == gender]


def validate_voice(voice_id: str, provider: str) -> str:
    """Validate voice ID for a provider. Returns valid voice or default fallback."""
    if provider == "openai":
        return voice_id if voice_id in OPENAI_VALID_VOICES else "ash"
    elif provider == "ultravox":
        return voice_id if voice_id in ULTRAVOX_VALID_VOICES else "Mark"
    elif provider == "xai":
        return voice_id if voice_id in XAI_VALID_VOICES else "Ara"
    elif provider == "gemini":
        return voice_id if voice_id in GEMINI_VALID_VOICES else "Kore"
    return voice_id
