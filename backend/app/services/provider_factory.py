"""
Factory for creating AI call provider instances.

Routes to the appropriate provider (OpenAI, Ultravox, xAI, or Gemini)
based on the agent's provider configuration.
"""

from app.services.call_provider import CallProvider


def get_provider(provider_type: str) -> CallProvider:
    """
    Get the appropriate call provider instance.

    Args:
        provider_type: "openai", "ultravox", "xai", or "gemini"

    Returns:
        CallProvider instance

    Raises:
        ValueError: If provider_type is not recognized
    """
    if provider_type == "openai":
        from app.services.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider_type == "ultravox":
        from app.services.ultravox_provider import UltravoxProvider
        return UltravoxProvider()
    elif provider_type in ("xai", "gemini"):
        # xAI and Gemini use the same Asterisk ARI flow as OpenAI
        # The provider field in Redis call_setup determines the WebSocket target
        from app.services.openai_provider import OpenAIProvider
        return OpenAIProvider()
    else:
        raise ValueError(f"Unknown call provider: {provider_type}. Use 'openai', 'ultravox', 'xai', or 'gemini'.")
