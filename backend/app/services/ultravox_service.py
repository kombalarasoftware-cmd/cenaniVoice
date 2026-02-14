"""
Ultravox REST API client.

Handles all HTTP communication with the Ultravox API including
call creation, management, transcript retrieval, and voice listing.
"""

import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default timeout for API requests
DEFAULT_TIMEOUT = 30.0


class UltravoxService:
    """Async HTTP client for the Ultravox REST API."""

    def __init__(self):
        self.base_url = settings.ULTRAVOX_BASE_URL.rstrip("/")
        self.api_key = settings.ULTRAVOX_API_KEY
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=DEFAULT_TIMEOUT,
        )

    # ------------------------------------------------------------------ Calls

    async def create_call(
        self,
        system_prompt: str,
        voice: str = "Mark",
        model: str = "ultravox-v0.7",
        temperature: float = 0.3,
        sip_to: str = "",
        sip_from: str = "",
        sip_username: str = "",
        sip_password: str = "",
        sip_trunk_host: str = "",
        sip_trunk_port: int = 5060,
        tools: Optional[list] = None,
        first_speaker: str = "user",
        recording_enabled: bool = True,
        max_duration: str = "300s",
        language_hint: str = "en",
        vad_settings: Optional[dict] = None,
        initial_messages: Optional[list] = None,
        greeting_text: Optional[str] = None,
        template_context: Optional[dict] = None,
        time_exceeded_message: Optional[str] = None,
        inactivity_messages: Optional[list] = None,
    ) -> dict:
        """
        Create an outbound SIP call via Ultravox API.

        Returns the full call object including callId and joinUrl.
        """
        # Build SIP destination URI
        if "@" not in sip_to:
            sip_to = f"sip:{sip_to}@{sip_trunk_host}:{sip_trunk_port}"

        # Build SIP from URI
        # Use SIP auth username in From header so Asterisk can identify the endpoint
        # CallerID is set by Asterisk dialplan, not from this field
        if sip_username:
            sip_from_uri = f"sip:{sip_username}@{sip_trunk_host}:{sip_trunk_port}"
        elif sip_from and "@" not in sip_from:
            sip_from_uri = f"sip:{sip_from}@{sip_trunk_host}"
        else:
            sip_from_uri = sip_from

        payload: dict[str, Any] = {
            "systemPrompt": system_prompt,
            "model": model,
            "voice": voice,
            "temperature": temperature,
            "languageHint": language_hint,
            "medium": {
                "sip": {
                    "outgoing": {
                        "to": sip_to,
                        "from": sip_from_uri,
                    }
                }
            },
            "recordingEnabled": recording_enabled,
            "maxDuration": max_duration,
        }

        # Add SIP authentication if credentials provided
        if sip_username:
            payload["medium"]["sip"]["outgoing"]["username"] = sip_username
        if sip_password:
            payload["medium"]["sip"]["outgoing"]["password"] = sip_password

        # First speaker configuration
        if first_speaker == "agent":
            agent_settings: dict[str, Any] = {}
            if greeting_text:
                agent_settings["text"] = greeting_text
            payload["firstSpeakerSettings"] = {"agent": agent_settings}
        else:
            payload["firstSpeakerSettings"] = {"user": {}}

        # Tools
        if tools:
            payload["selectedTools"] = tools

        # VAD settings
        if vad_settings:
            payload["vadSettings"] = vad_settings

        # Initial messages (for conversation history / context injection)
        if initial_messages:
            # Ultravox requires enum role values: MESSAGE_ROLE_AGENT, MESSAGE_ROLE_USER
            normalized = []
            for msg in initial_messages:
                role = msg.get("role", "")
                if role == "agent" or role == "assistant":
                    role = "MESSAGE_ROLE_AGENT"
                elif role == "user":
                    role = "MESSAGE_ROLE_USER"
                normalized.append({**msg, "role": role})
            payload["initialMessages"] = normalized

        # Template context variables
        if template_context:
            payload["templateContext"] = template_context

        # Time exceeded message (spoken before hanging up when max duration reached)
        if time_exceeded_message:
            payload["timeExceededMessage"] = time_exceeded_message

        # Inactivity messages — spoken when the user is silent for specified durations
        # Ultravox format: duration is a string like "30s", endBehavior is an enum
        if inactivity_messages:
            end_behavior_map = {
                "unspecified": "END_BEHAVIOR_UNSPECIFIED",
                "interruptible_hangup": "END_BEHAVIOR_UNSPECIFIED",
                "uninterruptible_hangup": "END_BEHAVIOR_UNSPECIFIED",
            }
            converted = []
            for msg in inactivity_messages:
                text = msg.get("message", "")
                if not text:
                    continue
                duration_sec = msg.get("duration", 30)
                behavior = msg.get("end_behavior", "unspecified")
                converted.append({
                    "duration": f"{duration_sec}s",
                    "message": text,
                    "endBehavior": end_behavior_map.get(behavior, "END_BEHAVIOR_UNSPECIFIED"),
                })
            if converted:
                payload["inactivityMessages"] = converted

        logger.info(f"Creating Ultravox call to {sip_to}")
        logger.debug(f"Ultravox payload: {json.dumps({k: v for k, v in payload.items() if k != 'systemPrompt'}, default=str)}")
        async with self._client() as client:
            response = await client.post("/calls", json=payload)
            if response.status_code >= 400:
                error_body = response.text
                logger.error(f"Ultravox API error {response.status_code}: {error_body}")
                response.raise_for_status()
            data = response.json()
            logger.info(f"Ultravox call created: {data.get('callId', 'unknown')}")
            return data

    async def get_call(self, call_id: str) -> dict:
        """Get call details by ID."""
        async with self._client() as client:
            response = await client.get(f"/calls/{call_id}")
            response.raise_for_status()
            return response.json()

    async def end_call(self, call_id: str, message: str = "") -> dict:
        """End an active call by sending a hang_up data message.

        Uses POST /calls/{call_id}/send_data_message with a hang_up payload.
        Ref: https://docs.ultravox.ai/api-reference/calls/calls-send-data-message-post

        Returns dict with 'joined' key:
        - joined=True: hang_up sent successfully (call was active)
        - joined=False: call was not joined yet or already ended (422)
        """
        async with self._client() as client:
            payload: dict[str, Any] = {"type": "hang_up"}
            if message:
                payload["message"] = message
            response = await client.post(
                f"/calls/{call_id}/send_data_message",
                json=payload,
            )
            if response.status_code in (200, 204):
                logger.info(f"Ultravox hang_up sent successfully for call {call_id[:8]}")
                return {"success": True, "joined": True, "message": "Call ended"}
            if response.status_code == 422:
                # Call was not joined yet (still ringing) or already ended
                # Caller should try DELETE to cancel the SIP leg
                logger.info(f"Ultravox call {call_id[:8]} not active (422) — needs DELETE to cancel SIP")
                return {"success": False, "joined": False, "message": "Call not joined"}
            response.raise_for_status()
            return {"success": True, "joined": True, "message": "Call ended"}

    async def delete_call(self, call_id: str) -> dict:
        """Delete a call record (for cleanup after call ends).

        NOTE: This does NOT terminate an active call — use end_call() for that.
        The DELETE endpoint returns 425 (Too Early) if the call is still active.
        """
        async with self._client() as client:
            response = await client.delete(f"/calls/{call_id}")
            if response.status_code in (200, 204, 404):
                return {"success": True, "message": "Call deleted"}
            if response.status_code == 425:
                logger.warning(f"Ultravox call {call_id[:8]} still active, cannot delete yet")
                return {"success": False, "message": "Call still active"}
            response.raise_for_status()
            return {"success": True, "message": "Call deleted"}

    async def get_call_messages(self, call_id: str) -> list:
        """
        Get call transcript messages.

        Returns a list of message objects with role, text, etc.
        """
        async with self._client() as client:
            response = await client.get(f"/calls/{call_id}/messages")
            response.raise_for_status()
            data = response.json()
            # Ultravox returns { results: [...] } or a list directly
            if isinstance(data, dict):
                return data.get("results", [])
            return data

    async def get_call_recording(self, call_id: str) -> Optional[str]:
        """
        Get call recording URL.

        Returns the recording download URL or None.
        """
        try:
            async with self._client() as client:
                response = await client.get(f"/calls/{call_id}/recording")
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
                return data.get("url") or data.get("recordingUrl")
        except httpx.HTTPStatusError:
            return None

    # --------------------------------------------------------------- Voices

    async def list_voices(self, language: Optional[str] = None) -> list:
        """
        List available Ultravox voices.

        Optionally filter by language code (e.g. 'en', 'tr').
        """
        params: dict[str, Any] = {"pageSize": 200}
        if language:
            params["primaryLanguage"] = language

        async with self._client() as client:
            response = await client.get("/voices", params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data.get("results", [])
            return data

    # -------------------------------------------------------------- Webhooks

    async def register_webhook(self, url: str, events: list[str]) -> dict:
        """Register a webhook URL for specific events."""
        payload = {
            "url": url,
            "events": events,
        }
        async with self._client() as client:
            response = await client.post("/webhooks", json=payload)
            response.raise_for_status()
            return response.json()

    async def list_webhooks(self) -> list:
        """List all registered webhooks."""
        async with self._client() as client:
            response = await client.get("/webhooks")
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return data.get("results", [])
            return data

    # --------------------------------------------------------- SIP Config

    async def get_sip_config(self) -> dict:
        """Get current SIP configuration."""
        async with self._client() as client:
            response = await client.get("/sip")
            response.raise_for_status()
            return response.json()

    async def update_sip_config(self, config: dict) -> dict:
        """Update SIP configuration (e.g. allowedCidrRanges)."""
        async with self._client() as client:
            response = await client.patch("/sip", json=config)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------ Agents

    async def create_agent(self, agent_config: dict) -> dict:
        """Create an Ultravox agent for agent-based calls."""
        async with self._client() as client:
            response = await client.post("/agents", json=agent_config)
            response.raise_for_status()
            return response.json()

    async def update_agent(self, agent_id: str, agent_config: dict) -> dict:
        """Update an existing Ultravox agent."""
        async with self._client() as client:
            response = await client.patch(f"/agents/{agent_id}", json=agent_config)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------ Corpus (RAG)

    async def create_corpus(self, name: str, description: str = "") -> dict:
        """Create a knowledge base corpus for RAG."""
        async with self._client() as client:
            response = await client.post(
                "/corpora",
                json={"name": name, "description": description},
            )
            response.raise_for_status()
            return response.json()
