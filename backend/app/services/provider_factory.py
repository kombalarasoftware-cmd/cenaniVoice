"""
Factory for creating AI call provider instances.

Routes to the appropriate provider (OpenAI or Ultravox) based on
the agent's provider configuration.
"""

from app.services.call_provider import CallProvider


def get_provider(provider_type: str) -> CallProvider:
    """
    Get the appropriate call provider instance.

    Args:
        provider_type: "openai", "ultravox", or "pipeline"

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
    elif provider_type == "pipeline":
        from app.services.pipeline_provider import PipelineProvider
        return PipelineProvider()
    else:
        raise ValueError(f"Unknown call provider: {provider_type}. Use 'openai', 'ultravox', or 'pipeline'.")
