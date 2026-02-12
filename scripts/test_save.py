"""Quick test to see 422 error detail from backend"""
import requests

BASE = "http://127.0.0.1:8000/api/v1"

# Login
r = requests.post(f"{BASE}/auth/login", json={
    "email": "cmutlu2006@hotmail.com",
    "password": "Speakmaxi2026!"
})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Full body like frontend sends
body = {
    "name": "Müşteri Memnuniyeti Anke",
    "provider": "pipeline",
    "prompt": {
        "role": "test",
        "personality": "",
        "context": "",
        "pronunciations": "",
        "sample_phrases": "",
        "tools": "",
        "rules": "",
        "flow": "",
        "safety": "",
        "language": ""
    },
    "voice_settings": {
        "model_type": "gpt-realtime-mini",
        "voice": "turkish-female",
        "language": "tr",
        "timezone": "Europe/Istanbul",
        "speech_speed": 1.0,
        "pipeline_voice": "turkish-female",
        "stt_provider": "deepgram",
        "llm_provider": "groq",
        "tts_provider": "cartesia",
        "stt_model": "",
        "llm_model": "",
        "tts_model": "",
        "tts_voice": ""
    },
    "call_settings": {
        "max_duration": 180,
        "silence_timeout": 10,
        "max_retries": 3,
        "retry_delay": 60
    },
    "behavior_settings": {
        "interruptible": True,
        "auto_transcribe": True,
        "record_calls": True,
        "human_transfer": False
    },
    "advanced_settings": {
        "temperature": 0.6,
        "vad_threshold": 0.3,
        "turn_detection": "server_vad",
        "vad_eagerness": "auto",
        "silence_duration_ms": 800,
        "prefix_padding_ms": 500,
        "idle_timeout_ms": None,
        "interrupt_response": True,
        "create_response": True,
        "noise_reduction": True,
        "max_output_tokens": 500,
        "transcript_model": "gpt-4o-transcribe"
    },
    "greeting_settings": {
        "first_speaker": "agent",
        "greeting_message": "Merhaba!",
        "greeting_uninterruptible": False,
        "first_message_delay": 0
    },
    "inactivity_messages": [],
    "knowledge_base": "",
    "web_sources": [],
    "smart_features": {
        "lead_capture": {
            "enabled": False,
            "triggers": [],
            "default_priority": 2,
            "auto_capture_phone": True,
            "auto_capture_address": False,
            "require_confirmation": True
        },
        "call_tags": {
            "enabled": False,
            "auto_tags": [],
            "tag_on_interest": True,
            "tag_on_rejection": True,
            "tag_on_callback": True
        },
        "callback": {
            "enabled": False,
            "default_delay_hours": 24,
            "max_attempts": 3,
            "respect_business_hours": True,
            "ask_preferred_time": True
        }
    },
    "survey_config": {
        "enabled": False,
        "questions": [],
        "start_question": None,
        "completion_message": "Thank you!",
        "abort_message": "Survey cancelled.",
        "allow_skip": False,
        "show_progress": True
    }
}

r2 = requests.put(f"{BASE}/agents/4", headers=headers, json=body)
print(f"Status: {r2.status_code}")
print(f"Response: {r2.text[:3000]}")

# Also GET the agent to see its current data
r3 = requests.get(f"{BASE}/agents/4", headers=headers)
import json
data = r3.json()

# Now try saving with the EXACT data from GET (roundtrip test)
body2 = {
    "name": data["name"],
    "provider": data["provider"],
    "prompt": {
        "role": data.get("prompt_role", "") or "",
        "personality": data.get("prompt_personality", "") or "",
        "context": data.get("prompt_context", "") or "",
        "pronunciations": data.get("prompt_pronunciations", "") or "",
        "sample_phrases": data.get("prompt_sample_phrases", "") or "",
        "tools": data.get("prompt_tools", "") or "",
        "rules": data.get("prompt_rules", "") or "",
        "flow": data.get("prompt_flow", "") or "",
        "safety": data.get("prompt_safety", "") or "",
        "language": ""
    },
    "voice_settings": {
        "model_type": data.get("model_type", "gpt-realtime-mini"),
        "voice": data.get("voice", "alloy"),
        "language": data.get("language", "tr"),
        "timezone": data.get("timezone", "Europe/Istanbul"),
        "speech_speed": data.get("speech_speed", 1.0),
        "pipeline_voice": data.get("voice", "turkish-female"),
        "stt_provider": data.get("stt_provider", "deepgram"),
        "llm_provider": data.get("llm_provider", "groq"),
        "tts_provider": data.get("tts_provider", "cartesia"),
        "stt_model": data.get("stt_model", "") or "",
        "llm_model": data.get("llm_model", "") or "",
        "tts_model": data.get("tts_model", "") or "",
        "tts_voice": data.get("tts_voice", "") or ""
    },
    "call_settings": {
        "max_duration": data.get("max_duration", 300),
        "silence_timeout": data.get("silence_timeout", 10),
        "max_retries": 3,
        "retry_delay": 60
    },
    "behavior_settings": {
        "interruptible": data.get("interruptible", True),
        "auto_transcribe": data.get("auto_transcribe", True),
        "record_calls": data.get("record_calls", True),
        "human_transfer": False
    },
    "advanced_settings": {
        "temperature": data.get("temperature", 0.7),
        "vad_threshold": data.get("vad_threshold", 0.3),
        "turn_detection": data.get("turn_detection", "server_vad"),
        "vad_eagerness": data.get("vad_eagerness", "auto"),
        "silence_duration_ms": data.get("silence_duration_ms", 800),
        "prefix_padding_ms": data.get("prefix_padding_ms", 500),
        "idle_timeout_ms": data.get("idle_timeout_ms"),
        "interrupt_response": data.get("interrupt_response", True),
        "create_response": data.get("create_response", True),
        "noise_reduction": data.get("noise_reduction", True),
        "max_output_tokens": data.get("max_output_tokens", 500),
        "transcript_model": data.get("transcript_model", "gpt-4o-transcribe")
    },
    "greeting_settings": {
        "first_speaker": data.get("first_speaker", "agent"),
        "greeting_message": data.get("greeting_message", ""),
        "greeting_uninterruptible": data.get("greeting_uninterruptible", False),
        "first_message_delay": data.get("first_message_delay", 0.0)
    },
    "inactivity_messages": data.get("inactivity_messages", []),
    "knowledge_base": data.get("knowledge_base", ""),
    "web_sources": data.get("web_sources", []),
    "smart_features": data.get("smart_features", {}),
    "survey_config": data.get("survey_config", {})
}

r4 = requests.put(f"{BASE}/agents/4", headers=headers, json=body2)
print(f"\n--- Roundtrip save status: {r4.status_code} ---")
print(f"Response: {r4.text[:3000]}")

# GET the DETAIL endpoint for full survey questions
r5 = requests.get(f"{BASE}/agents/4", headers=headers)
detail = r5.json()
sq = detail.get("survey_config", {}).get("questions", [])
print(f"\n--- Survey questions count: {len(sq)} ---")
if sq:
    print(json.dumps(sq[:2], indent=2, ensure_ascii=False)[:2000])

# Try saving WITH the actual survey questions
body2["survey_config"]["questions"] = sq
body2["survey_config"]["enabled"] = detail.get("survey_config", {}).get("enabled", False)
body2["survey_config"]["start_question"] = detail.get("survey_config", {}).get("start_question")
r6 = requests.put(f"{BASE}/agents/4", headers=headers, json=body2)
print(f"\n--- Save with survey questions status: {r6.status_code} ---")
print(f"Response: {r6.text[:3000]}")
