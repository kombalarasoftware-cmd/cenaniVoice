"""
Real-time event streaming and cost tracking API endpoints
Uses Server-Sent Events (SSE) for live event streaming
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, AsyncGenerator
from datetime import datetime
from decimal import Decimal
import json
import asyncio
import logging
import redis.asyncio as aioredis
import os

from app.core.database import get_db
from app.api.v1.auth import get_current_user, get_current_user_optional
from app.models import User

router = APIRouter(prefix="/events", tags=["Events"])
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# OpenAI Realtime API Pricing (February 2026)
# https://openai.com/api/pricing/
PRICING = {
    "gpt-realtime": {
        "input_text": Decimal("4.00") / 1_000_000,      # $4.00 per 1M tokens
        "cached_input_text": Decimal("0.40") / 1_000_000, # $0.40 per 1M cached tokens
        "output_text": Decimal("16.00") / 1_000_000,    # $16.00 per 1M tokens
        "input_audio": Decimal("32.00") / 1_000_000,    # $32.00 per 1M tokens
        "cached_input_audio": Decimal("0.40") / 1_000_000, # $0.40 per 1M cached tokens
        "output_audio": Decimal("64.00") / 1_000_000,   # $64.00 per 1M tokens
    },
    "gpt-realtime-mini": {
        "input_text": Decimal("0.60") / 1_000_000,      # $0.60 per 1M tokens
        "cached_input_text": Decimal("0.06") / 1_000_000, # $0.06 per 1M cached tokens
        "output_text": Decimal("2.40") / 1_000_000,     # $2.40 per 1M tokens
        "input_audio": Decimal("10.00") / 1_000_000,    # $10.00 per 1M tokens
        "cached_input_audio": Decimal("0.30") / 1_000_000, # $0.30 per 1M cached tokens
        "output_audio": Decimal("20.00") / 1_000_000,   # $20.00 per 1M tokens
    },
}


def calculate_cost(usage: dict, model: str = "gpt-realtime-mini") -> dict:
    """
    Calculate cost from token usage.
    Usage format from OpenAI rate_limits.updated event:
    {
        "input_tokens": 100,
        "output_tokens": 50,
        "input_token_details": {"cached_tokens": 0, "text_tokens": 80, "audio_tokens": 20},
        "output_token_details": {"text_tokens": 30, "audio_tokens": 20}
    }
    """
    pricing = PRICING.get(model, PRICING["gpt-realtime-mini"])
    
    input_details = usage.get("input_token_details", {})
    output_details = usage.get("output_token_details", {})
    
    input_text = input_details.get("text_tokens", 0)
    input_audio = input_details.get("audio_tokens", 0)
    output_text = output_details.get("text_tokens", 0)
    output_audio = output_details.get("audio_tokens", 0)
    
    # If no details, estimate 80% text, 20% audio
    if not input_details:
        total_input = usage.get("input_tokens", 0)
        input_text = int(total_input * 0.8)
        input_audio = total_input - input_text
    
    if not output_details:
        total_output = usage.get("output_tokens", 0)
        output_text = int(total_output * 0.8)
        output_audio = total_output - output_text
    
    cost_input_text = input_text * pricing["input_text"]
    cost_input_audio = input_audio * pricing["input_audio"]
    cost_output_text = output_text * pricing["output_text"]
    cost_output_audio = output_audio * pricing["output_audio"]
    
    total_cost = cost_input_text + cost_input_audio + cost_output_text + cost_output_audio
    
    return {
        "input_tokens": {
            "text": input_text,
            "audio": input_audio,
            "total": input_text + input_audio,
        },
        "output_tokens": {
            "text": output_text,
            "audio": output_audio,
            "total": output_text + output_audio,
        },
        "cost": {
            "input_text": float(cost_input_text),
            "input_audio": float(cost_input_audio),
            "output_text": float(cost_output_text),
            "output_audio": float(cost_output_audio),
            "total": float(total_cost),
        },
        "model": model,
    }


async def event_generator(call_id: str) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a specific call.
    Subscribes to Redis pub/sub channel for real-time events.
    """
    try:
        redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        pubsub = redis.pubsub()
        channel = f"call_events:{call_id}"
        
        await pubsub.subscribe(channel)
        logger.info(f"SSE client subscribed to {channel}")
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'call_id': call_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        
        # Keep connection alive and stream events
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=30.0  # Send heartbeat every 30 seconds
                )
                
                if message and message["type"] == "message":
                    data = message["data"]
                    yield f"data: {data}\n\n"
                else:
                    # Heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                    
            except asyncio.TimeoutError:
                # Heartbeat on timeout
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                
    except asyncio.CancelledError:
        logger.info(f"SSE connection cancelled for {call_id}")
    except Exception as e:
        logger.error(f"SSE error for {call_id}: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        if 'pubsub' in locals():
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        if 'redis' in locals():
            await redis.close()


@router.get("/stream/{call_id}")
async def stream_call_events(
    call_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Stream real-time events for a call using Server-Sent Events (SSE).
    
    Events include:
    - session.created, session.updated
    - input_audio_buffer.speech_started, speech_stopped
    - conversation.item.input_audio_transcription.completed
    - response.audio_transcript.delta, response.done
    - rate_limits.updated (includes token usage)
    - error
    """
    return StreamingResponse(
        event_generator(call_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/cost/{call_id}")
async def get_call_cost(
    call_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get cost breakdown for a specific call.
    Retrieves usage data from Redis.
    """
    try:
        redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        
        # Get usage data from Redis
        usage_key = f"call_usage:{call_id}"
        usage_data = await redis.get(usage_key)
        
        await redis.close()
        
        if not usage_data:
            return {
                "call_id": call_id,
                "usage": None,
                "cost": None,
                "message": "No usage data available yet"
            }
        
        usage = json.loads(usage_data)
        model = usage.get("model", "gpt-realtime-mini")
        cost_breakdown = calculate_cost(usage, model)
        
        return {
            "call_id": call_id,
            "usage": usage,
            "cost": cost_breakdown,
        }
        
    except Exception as e:
        logger.error(f"Error getting call cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/summary")
async def get_usage_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated usage and cost summary.
    """
    # TODO: Implement aggregated usage from database
    return {
        "period": {
            "start": start_date or "today",
            "end": end_date or "today",
        },
        "total_calls": 0,
        "total_duration_seconds": 0,
        "total_tokens": {
            "input": 0,
            "output": 0,
        },
        "total_cost": 0.0,
        "by_model": {},
    }
