"""
Cloud LLM (Large Language Model) Providers
============================================
Supported providers:
  - Groq (OpenAI-compatible, ultra-fast inference)
  - OpenAI (GPT-4o, GPT-4o-mini)
  - Cerebras (OpenAI-compatible, fastest inference)

All providers use OpenAI-compatible chat/completions API with streaming.
"""

import json
import time
import logging
from typing import List, Dict, Optional, AsyncGenerator

import httpx

logger = logging.getLogger("pipeline-bridge")


# ============================================================================
# PROVIDER CONFIGS
# ============================================================================

LLM_PROVIDER_CONFIGS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "label": "Groq",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
        ],
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "label": "OpenAI",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1-nano",
            "gpt-4.1-mini",
        ],
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1/chat/completions",
        "label": "Cerebras",
        "models": [
            "llama-3.3-70b",
            "llama3.1-8b",
            "qwen-3-32b",
        ],
        "default_model": "llama-3.3-70b",
        "env_key": "CEREBRAS_API_KEY",
    },
}


# ============================================================================
# LLM STREAMING (OpenAI-Compatible for all providers)
# ============================================================================

async def cloud_llm_streaming(
    messages: List[Dict[str, str]],
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 300,
) -> AsyncGenerator[str, None]:
    """
    Stream LLM response from any OpenAI-compatible provider.

    All three providers (Groq, OpenAI, Cerebras) use the same
    OpenAI chat/completions streaming format (SSE).

    Yields text chunks as they arrive for sentence-level TTS pipelining.
    """
    config = LLM_PROVIDER_CONFIGS.get(provider)
    if not config:
        logger.error(f"Unknown LLM provider: {provider}")
        return

    model = model or config["default_model"]
    url = config["base_url"]

    t0 = time.monotonic()
    first_token_time = None
    total_tokens = 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "temperature": temperature,
                    "max_completion_tokens": max_tokens,
                    "top_p": 0.9,
                },
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(
                        f"{config['label']} LLM error {response.status_code}: "
                        f"{error_body.decode()[:300]}"
                    )
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            if first_token_time is None:
                                first_token_time = (time.monotonic() - t0) * 1000
                            total_tokens += 1
                            yield content

                        # Check finish reason
                        finish = data.get("choices", [{}])[0].get("finish_reason")
                        if finish:
                            break

                    except json.JSONDecodeError:
                        continue

    except Exception as e:
        logger.error(f"{config['label']} LLM streaming error: {e}")

    finally:
        total_time = (time.monotonic() - t0) * 1000
        ttft = first_token_time or 0
        logger.info(
            f"{config['label']} LLM: model={model} TTFT={ttft:.0f}ms "
            f"total={total_time:.0f}ms chunks={total_tokens}"
        )


# ============================================================================
# LLM NON-STREAMING (for simple use cases)
# ============================================================================

async def cloud_llm_generate(
    messages: List[Dict[str, str]],
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 300,
) -> str:
    """
    Non-streaming LLM response.
    Returns the full response text.
    """
    config = LLM_PROVIDER_CONFIGS.get(provider)
    if not config:
        logger.error(f"Unknown LLM provider: {provider}")
        return ""

    model = model or config["default_model"]
    url = config["base_url"]

    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "temperature": temperature,
                    "max_completion_tokens": max_tokens,
                    "top_p": 0.9,
                },
            )

            elapsed = (time.monotonic() - t0) * 1000

            if response.status_code != 200:
                logger.error(
                    f"{config['label']} LLM error {response.status_code}: "
                    f"{response.text[:300]}"
                )
                return ""

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            logger.info(
                f"{config['label']} LLM: model={model} "
                f"time={elapsed:.0f}ms response='{content[:80]}...'"
            )
            return content

    except Exception as e:
        logger.error(f"{config['label']} LLM error: {e}")
        return ""
