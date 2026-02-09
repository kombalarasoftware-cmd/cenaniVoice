"""
Abstract base class for AI call providers.

Defines the common interface that both OpenAI Realtime and Ultravox
providers must implement. This allows the system to route calls
to the appropriate provider based on agent configuration.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CallProvider(ABC):
    """Abstract interface for AI voice call providers."""

    @abstractmethod
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
        """
        Start an outbound call.

        Returns:
            dict with keys:
                - call_id: str (unique identifier for tracking)
                - ultravox_call_id: str | None (Ultravox-specific ID)
                - channel_id: str | None (Asterisk channel ID, OpenAI only)
                - status: str
        """

    @abstractmethod
    async def end_call(self, call_id: str) -> dict:
        """
        Terminate an active call.

        Returns:
            dict with keys:
                - success: bool
                - message: str
        """

    @abstractmethod
    async def get_transcript(self, call_id: str) -> list:
        """
        Get call transcript messages.

        Returns:
            list of dicts with keys:
                - role: "user" | "assistant"
                - content: str
                - timestamp: str (ISO 8601)
        """

    @abstractmethod
    async def get_recording_url(self, call_id: str) -> Optional[str]:
        """
        Get call recording URL.

        Returns:
            URL string or None if not available.
        """

    @abstractmethod
    def calculate_cost(self, duration_seconds: int, **kwargs) -> dict:
        """
        Calculate call cost based on provider pricing.

        Returns:
            dict with keys:
                - provider: str ("openai" | "ultravox")
                - duration_seconds: int
                - total_cost_usd: float
                - (provider-specific fields)
        """
