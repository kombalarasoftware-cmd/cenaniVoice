"""
OpenAI Realtime API Client for Voice AI Platform
Handles WebSocket connection to OpenAI Realtime API and audio streaming

Supports two models:
- gpt-realtime: Premium model ($32/$64 per 1M tokens) - Complex tasks, VIP customers
- gpt-realtime-mini: Economic model ($10/$20 per 1M tokens) - Routine tasks, high volume
"""

import asyncio
import json
import base64
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class RealtimeModelType(str, Enum):
    """Available OpenAI Realtime models"""
    GPT_REALTIME = "gpt-realtime"
    GPT_REALTIME_MINI = "gpt-realtime-mini"


# Pricing per 1M tokens (USD)
MODEL_PRICING = {
    RealtimeModelType.GPT_REALTIME: {
        "input": 32.00,
        "cached": 0.40,
        "output": 64.00,
    },
    RealtimeModelType.GPT_REALTIME_MINI: {
        "input": 10.00,
        "cached": 0.30,
        "output": 20.00,
    },
}


@dataclass
class TokenUsage:
    """Track token usage and cost"""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    
    def calculate_cost(self, model: RealtimeModelType) -> float:
        """Calculate estimated cost in USD"""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING[RealtimeModelType.GPT_REALTIME_MINI])
        
        # Convert to per-token cost (pricing is per 1M tokens)
        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        cached_cost = (self.cached_tokens / 1_000_000) * pricing["cached"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        
        return round(input_cost + cached_cost + output_cost, 6)


@dataclass
class RealtimeConfig:
    """Configuration for OpenAI Realtime session"""
    model: RealtimeModelType = RealtimeModelType.GPT_REALTIME_MINI  # Default to economic
    voice: str = "alloy"
    language: str = "tr"
    temperature: float = 0.7
    max_response_output_tokens: int = 4096
    turn_detection_type: str = "server_vad"
    turn_detection_threshold: float = 0.5
    turn_detection_prefix_padding_ms: int = 300
    turn_detection_silence_duration_ms: int = 500
    input_audio_format: str = "pcm16"
    output_audio_format: str = "pcm16"
    
    @property
    def model_name(self) -> str:
        """Get the model name for API calls"""
        return self.model.value


class OpenAIRealtimeClient:
    """
    Client for OpenAI Realtime API
    
    Handles:
    - WebSocket connection management
    - Audio streaming (input/output)
    - Event handling (transcription, responses, etc.)
    - Tool/function calling
    - Token usage and cost tracking
    """
    
    REALTIME_API_URL = "wss://api.openai.com/v1/realtime"
    
    def __init__(
        self,
        api_key: str,
        config: Optional[RealtimeConfig] = None,
        on_audio: Optional[Callable[[bytes], None]] = None,
        on_transcript: Optional[Callable[[str, str], None]] = None,  # (role, text)
        on_response_done: Optional[Callable[[Dict], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, Dict], Any]] = None,
    ):
        self.api_key = api_key
        self.config = config or RealtimeConfig()
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        
        # Callbacks
        self.on_audio = on_audio
        self.on_transcript = on_transcript
        self.on_response_done = on_response_done
        self.on_error = on_error
        self.on_tool_call = on_tool_call
        
        # State
        self.session_id: Optional[str] = None
        self.conversation_items: list = []
        
        # Token usage tracking
        self.token_usage = TokenUsage()
        
    async def connect(self, system_prompt: Optional[str] = None, tools: Optional[list] = None):
        """Establish WebSocket connection to OpenAI Realtime API"""
        url = f"{self.REALTIME_API_URL}?model={self.config.model_name}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        try:
            self.websocket = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            self.is_connected = True
            logger.info("Connected to OpenAI Realtime API")
            
            # Configure session
            await self._configure_session(system_prompt, tools)
            
            # Start receiving messages
            asyncio.create_task(self._receive_messages())
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            if self.on_error:
                self.on_error(str(e))
            raise
    
    async def _configure_session(self, system_prompt: Optional[str] = None, tools: Optional[list] = None):
        """Configure the realtime session"""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": self.config.voice,
                "input_audio_format": self.config.input_audio_format,
                "output_audio_format": self.config.output_audio_format,
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": self.config.turn_detection_type,
                    "threshold": self.config.turn_detection_threshold,
                    "prefix_padding_ms": self.config.turn_detection_prefix_padding_ms,
                    "silence_duration_ms": self.config.turn_detection_silence_duration_ms
                },
                "temperature": self.config.temperature,
                "max_response_output_tokens": self.config.max_response_output_tokens
            }
        }
        
        # Add system prompt
        if system_prompt:
            session_config["session"]["instructions"] = system_prompt
        
        # Add tools
        if tools:
            session_config["session"]["tools"] = tools
            session_config["session"]["tool_choice"] = "auto"
        
        await self._send(session_config)
    
    async def _send(self, message: dict):
        """Send a message to the WebSocket"""
        if self.websocket and self.is_connected:
            await self.websocket.send(json.dumps(message))
    
    async def _receive_messages(self):
        """Receive and process messages from WebSocket"""
        if not self.websocket:
            return
        try:
            async for message in self.websocket:
                await self._handle_message(json.loads(message))
        except ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            if self.on_error:
                self.on_error(str(e))
    
    async def _handle_message(self, message: dict):
        """Handle incoming WebSocket message"""
        event_type = message.get("type", "")
        
        if event_type == "session.created":
            self.session_id = message.get("session", {}).get("id")
            logger.info(f"Session created: {self.session_id}")
        
        elif event_type == "session.updated":
            logger.debug("Session updated")
        
        elif event_type == "response.audio.delta":
            # Audio chunk from AI
            audio_base64 = message.get("delta", "")
            if audio_base64 and self.on_audio:
                audio_bytes = base64.b64decode(audio_base64)
                self.on_audio(audio_bytes)
        
        elif event_type == "response.audio_transcript.delta":
            # AI speech transcription
            transcript = message.get("delta", "")
            if transcript and self.on_transcript:
                self.on_transcript("assistant", transcript)
        
        elif event_type == "conversation.item.input_audio_transcription.completed":
            # User speech transcription
            transcript = message.get("transcript", "")
            if transcript and self.on_transcript:
                self.on_transcript("user", transcript)
        
        elif event_type == "response.done":
            # Response completed - track token usage
            response = message.get("response", {})
            usage = response.get("usage", {})
            
            if usage:
                self.token_usage.input_tokens += usage.get("input_tokens", 0)
                self.token_usage.output_tokens += usage.get("output_tokens", 0)
                self.token_usage.cached_tokens += usage.get("cached_tokens", 0)
                
                cost = self.token_usage.calculate_cost(self.config.model)
                logger.debug(
                    f"Token usage - in: {self.token_usage.input_tokens}, "
                    f"out: {self.token_usage.output_tokens}, "
                    f"cached: {self.token_usage.cached_tokens}, "
                    f"cost: ${cost:.4f}"
                )
            
            if self.on_response_done:
                self.on_response_done(message)
        
        elif event_type == "response.function_call_arguments.done":
            # Tool/function call completed
            await self._handle_tool_call(message)
        
        elif event_type == "error":
            error_msg = message.get("error", {}).get("message", "Unknown error")
            logger.error(f"API Error: {error_msg}")
            if self.on_error:
                self.on_error(error_msg)
    
    async def _handle_tool_call(self, message: dict):
        """Handle tool/function call from AI"""
        call_id = message.get("call_id")
        name = message.get("name") or ""
        arguments = json.loads(message.get("arguments", "{}"))
        
        logger.info(f"Tool call: {name}({arguments})")
        
        if self.on_tool_call:
            try:
                result = await self.on_tool_call(name, arguments)
                
                # Send tool result back
                await self._send({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result)
                    }
                })
                
                # Request response continuation
                await self._send({"type": "response.create"})
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                await self._send({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps({"error": str(e)})
                    }
                })
    
    async def send_audio(self, audio_bytes: bytes):
        """Send audio chunk to the API"""
        if not self.is_connected:
            return
        
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        await self._send({
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        })
    
    async def commit_audio(self):
        """Commit audio buffer and request response"""
        await self._send({"type": "input_audio_buffer.commit"})
    
    async def send_text(self, text: str):
        """Send text message to the conversation"""
        await self._send({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        })
        
        # Request response
        await self._send({"type": "response.create"})
    
    async def interrupt(self):
        """Interrupt current response"""
        await self._send({"type": "response.cancel"})
    
    async def disconnect(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from OpenAI Realtime API")


def build_system_prompt(agent_config: dict, customer_data: Optional[dict] = None) -> str:
    """
    Build system prompt from agent configuration and customer data
    
    Args:
        agent_config: Agent settings from database
        customer_data: Customer-specific data for personalization
    
    Returns:
        Complete system prompt string
    """
    sections = []
    
    # Role
    if agent_config.get("prompt_role"):
        sections.append(f"## Role\n{agent_config['prompt_role']}")
    
    # Personality
    if agent_config.get("prompt_personality"):
        sections.append(f"## Personality\n{agent_config['prompt_personality']}")
    
    # Language
    if agent_config.get("prompt_language"):
        sections.append(f"## Language Guidelines\n{agent_config['prompt_language']}")
    
    # Flow
    if agent_config.get("prompt_flow"):
        sections.append(f"## Conversation Flow\n{agent_config['prompt_flow']}")
    
    # Tools
    if agent_config.get("prompt_tools"):
        sections.append(f"## Available Tools\n{agent_config['prompt_tools']}")
    
    # Safety
    if agent_config.get("prompt_safety"):
        sections.append(f"## Safety Rules\n{agent_config['prompt_safety']}")
    
    # Rules
    if agent_config.get("prompt_rules"):
        sections.append(f"## Important Rules\n{agent_config['prompt_rules']}")
    
    prompt = "\n\n".join(sections)
    
    # Inject customer data
    if customer_data:
        prompt = prompt.replace("{{customer_name}}", customer_data.get("name", "Değerli müşterimiz"))
        prompt = prompt.replace("{{phone}}", customer_data.get("phone", ""))
        
        # Custom fields
        for key, value in customer_data.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
    
    return prompt


def build_tools(agent_config: dict) -> list:
    """
    Build tool definitions for the AI agent
    
    Returns list of tool definitions for OpenAI function calling
    """
    tools = []
    
    # Payment promise tool
    if agent_config.get("human_transfer"):
        tools.append({
            "type": "function",
            "name": "record_payment_promise",
            "description": "Müşteri ödeme sözü verdiğinde bu fonksiyonu çağır",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Ödeme tutarı"
                    },
                    "date": {
                        "type": "string",
                        "description": "Ödeme tarihi (YYYY-MM-DD)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Ek notlar"
                    }
                },
                "required": ["amount", "date"]
            }
        })
    
    # Transfer to human
    if agent_config.get("human_transfer"):
        tools.append({
            "type": "function",
            "name": "transfer_to_human",
            "description": "Müşteri yetkili bir kişiyle görüşmek istediğinde veya çözülemeyen bir sorun olduğunda",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Transfer nedeni"
                    }
                },
                "required": ["reason"]
            }
        })
    
    # Schedule callback
    tools.append({
        "type": "function",
        "name": "schedule_callback",
        "description": "Müşteri daha sonra aranmak istediğinde",
        "parameters": {
            "type": "object",
            "properties": {
                "datetime": {
                    "type": "string",
                    "description": "Geri arama zamanı (YYYY-MM-DD HH:MM)"
                },
                "notes": {
                    "type": "string",
                    "description": "Notlar"
                }
            },
            "required": ["datetime"]
        }
    })
    
    # End call
    tools.append({
        "type": "function",
        "name": "end_call",
        "description": "Görüşmeyi sonlandır",
        "parameters": {
            "type": "object",
            "properties": {
                "outcome": {
                    "type": "string",
                    "enum": ["success", "no_interest", "wrong_number", "callback", "other"],
                    "description": "Görüşme sonucu"
                },
                "summary": {
                    "type": "string",
                    "description": "Görüşme özeti"
                }
            },
            "required": ["outcome"]
        }
    })
    
    return tools


# ============================================================================
# MODEL SELECTION HELPERS
# ============================================================================

def select_optimal_model(
    task_complexity: str = "routine",
    customer_tier: str = "standard",
    budget_mode: bool = True
) -> RealtimeModelType:
    """
    Select the optimal model based on task requirements.
    
    Args:
        task_complexity: "routine" | "complex" - Task difficulty
        customer_tier: "standard" | "vip" - Customer importance
        budget_mode: If True, prefer mini model for cost savings
    
    Returns:
        RealtimeModelType: Selected model
        
    Pricing Reference:
        gpt-realtime:      $32 input / $64 output per 1M tokens
        gpt-realtime-mini: $10 input / $20 output per 1M tokens
        
    Cost savings: ~70% with mini model
    """
    # VIP customers or complex tasks get premium model
    if customer_tier == "vip" or task_complexity == "complex":
        return RealtimeModelType.GPT_REALTIME
    
    # Budget mode or routine tasks get mini model
    if budget_mode or task_complexity == "routine":
        return RealtimeModelType.GPT_REALTIME_MINI
    
    # Default to mini for cost efficiency
    return RealtimeModelType.GPT_REALTIME_MINI


def estimate_call_cost(
    duration_seconds: int,
    model: RealtimeModelType = RealtimeModelType.GPT_REALTIME_MINI,
    avg_tokens_per_minute: int = 1500
) -> dict:
    """
    Estimate the cost of a call before it happens.
    
    Args:
        duration_seconds: Expected call duration
        model: Model to use
        avg_tokens_per_minute: Average token consumption (input + output)
        
    Returns:
        dict with estimated costs
    """
    duration_minutes = duration_seconds / 60
    total_tokens = int(duration_minutes * avg_tokens_per_minute)
    
    # Assume 60% input, 40% output ratio
    input_tokens = int(total_tokens * 0.6)
    output_tokens = int(total_tokens * 0.4)
    
    pricing = MODEL_PRICING[model]
    
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost
    
    return {
        "model": model.value,
        "duration_minutes": round(duration_minutes, 1),
        "estimated_tokens": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": round(total_cost, 4),
        "cost_per_minute": round(total_cost / max(duration_minutes, 0.1), 4),
    }


def compare_model_costs(duration_seconds: int = 300) -> dict:
    """
    Compare costs between models for a given call duration.
    
    Args:
        duration_seconds: Call duration (default 5 minutes)
        
    Returns:
        dict with cost comparison
    """
    premium = estimate_call_cost(duration_seconds, RealtimeModelType.GPT_REALTIME)
    mini = estimate_call_cost(duration_seconds, RealtimeModelType.GPT_REALTIME_MINI)
    
    savings = premium["estimated_cost_usd"] - mini["estimated_cost_usd"]
    savings_percent = (savings / premium["estimated_cost_usd"]) * 100 if premium["estimated_cost_usd"] > 0 else 0
    
    return {
        "duration_minutes": premium["duration_minutes"],
        "gpt_realtime": premium,
        "gpt_realtime_mini": mini,
        "savings_usd": round(savings, 4),
        "savings_percent": round(savings_percent, 1),
        "recommendation": "Use gpt-realtime-mini for routine calls to save ~70% on costs"
    }

