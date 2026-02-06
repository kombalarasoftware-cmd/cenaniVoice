"""
Asterisk ARI (Asterisk REST Interface) Client
Handles communication with Asterisk PBX for call control
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any, Awaitable, Union
from dataclasses import dataclass
import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


@dataclass
class ARIConfig:
    """Configuration for Asterisk ARI connection"""
    host: str = "localhost"
    port: int = 8088
    username: str = "voiceai"
    password: str = "voiceai_secret"
    app_name: str = "voiceai"
    use_ssl: bool = False


# Callback type that supports both sync and async functions
CallbackType = Union[Callable[[str, Dict], None], Callable[[str, Dict], Awaitable[None]]]
AudioCallbackType = Union[Callable[[str, bytes], None], Callable[[str, bytes], Awaitable[None]]]
DTMFCallbackType = Union[Callable[[str, str], None], Callable[[str, str], Awaitable[None]]]


class AsteriskARIClient:
    """
    Client for Asterisk ARI (Asterisk REST Interface)
    
    Handles:
    - WebSocket connection for events
    - REST API calls for call control
    - Audio bridging
    - Call state management
    """
    
    def __init__(
        self,
        config: Optional[ARIConfig] = None,
        on_call_start: Optional[CallbackType] = None,
        on_call_answer: Optional[CallbackType] = None,
        on_call_end: Optional[CallbackType] = None,
        on_dtmf: Optional[DTMFCallbackType] = None,
        on_audio: Optional[AudioCallbackType] = None,
    ):
        self.config = config or ARIConfig()
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        
        # Callbacks
        self.on_call_start = on_call_start
        self.on_call_answer = on_call_answer
        self.on_call_end = on_call_end
        self.on_dtmf = on_dtmf
        self.on_audio = on_audio
        
        # Active channels and bridges
        self.channels: Dict[str, Dict] = {}
        self.bridges: Dict[str, Dict] = {}
        
        # Build URLs
        protocol = "https" if self.config.use_ssl else "http"
        ws_protocol = "wss" if self.config.use_ssl else "ws"
        self.base_url = f"{protocol}://{self.config.host}:{self.config.port}/ari"
        self.ws_url = f"{ws_protocol}://{self.config.host}:{self.config.port}/ari/events"
    
    async def connect(self):
        """Establish connection to Asterisk ARI"""
        # Create HTTP session for REST calls
        auth = aiohttp.BasicAuth(self.config.username, self.config.password)
        self.session = aiohttp.ClientSession(auth=auth)
        
        # Connect to WebSocket for events
        ws_url = f"{self.ws_url}?app={self.config.app_name}&api_key={self.config.username}:{self.config.password}"
        
        try:
            self.websocket = await websockets.connect(ws_url)
            self.is_connected = True
            logger.info("Connected to Asterisk ARI")
            
            # Start receiving events
            asyncio.create_task(self._receive_events())
            
        except Exception as e:
            logger.error(f"Failed to connect to ARI: {e}")
            raise
    
    async def _receive_events(self):
        """Receive and process ARI events"""
        if not self.websocket:
            return
        try:
            async for message in self.websocket:
                event = json.loads(message)
                await self._handle_event(event)
        except ConnectionClosed:
            logger.info("ARI WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error receiving ARI events: {e}")
    
    async def _handle_event(self, event: dict):
        """Handle incoming ARI event"""
        event_type = event.get("type", "")
        
        if event_type == "StasisStart":
            # New channel entered application
            channel = event.get("channel", {})
            channel_id = channel.get("id")
            
            self.channels[channel_id] = channel
            logger.info(f"Channel started: {channel_id}")
            
            if self.on_call_start:
                self.on_call_start(channel_id, channel)
        
        elif event_type == "StasisEnd":
            # Channel left application
            channel = event.get("channel", {})
            channel_id = channel.get("id")
            
            if channel_id in self.channels:
                del self.channels[channel_id]
            
            logger.info(f"Channel ended: {channel_id}")
            
            if self.on_call_end:
                self.on_call_end(channel_id, channel)
        
        elif event_type == "ChannelStateChange":
            # Channel state changed
            channel = event.get("channel", {})
            channel_id = channel.get("id")
            state = channel.get("state")
            
            if state == "Up" and self.on_call_answer:
                self.on_call_answer(channel_id, channel)
        
        elif event_type == "ChannelDtmfReceived":
            # DTMF digit received
            channel_id = event.get("channel", {}).get("id")
            digit = event.get("digit")
            
            if self.on_dtmf and channel_id and digit:
                self.on_dtmf(channel_id, digit)
    
    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        """Make REST API call to ARI"""
        if not self.session:
            raise Exception("Session not initialized")
        url = f"{self.base_url}/{endpoint}"
        
        async with self.session.request(method, url, **kwargs) as response:
            if response.status >= 400:
                text = await response.text()
                logger.error(f"ARI API error: {response.status} - {text}")
                raise Exception(f"ARI API error: {response.status}")
            
            if response.content_type == "application/json":
                return await response.json()
            return {}
    
    async def originate_call(
        self,
        endpoint: str,
        caller_id: Optional[str] = None,
        variables: Optional[dict] = None
    ) -> str:
        """
        Originate an outbound call
        
        Args:
            endpoint: SIP endpoint (e.g., "PJSIP/+905321234567@trunk")
            caller_id: Caller ID to display
            variables: Channel variables
        
        Returns:
            Channel ID
        """
        data: Dict[str, Any] = {
            "endpoint": endpoint,
            "app": self.config.app_name,
            "appArgs": "outbound",
        }
        
        if caller_id:
            data["callerId"] = caller_id
        
        if variables:
            data["variables"] = variables
        
        result = await self._api_call("POST", "channels", json=data)
        channel_id = result.get("id") if result else None
        
        if not channel_id:
            raise Exception("Failed to originate call - no channel ID returned")
        
        logger.info(f"Originated call: {channel_id} -> {endpoint}")
        return channel_id
    
    async def answer_channel(self, channel_id: str):
        """Answer a channel"""
        await self._api_call("POST", f"channels/{channel_id}/answer")
        logger.info(f"Answered channel: {channel_id}")
    
    async def hangup_channel(self, channel_id: str, reason: str = "normal"):
        """Hangup a channel"""
        await self._api_call(
            "DELETE", 
            f"channels/{channel_id}",
            params={"reason_code": reason}
        )
        logger.info(f"Hung up channel: {channel_id}")
    
    async def create_bridge(self, bridge_type: str = "mixing") -> str:
        """Create a bridge for audio mixing"""
        result = await self._api_call(
            "POST",
            "bridges",
            json={"type": bridge_type, "name": f"voiceai_{id(self)}"}
        )
        bridge_id = result.get("id") if result else None
        
        if not bridge_id:
            raise Exception("Failed to create bridge - no bridge ID returned")
        
        self.bridges[bridge_id] = result or {}
        
        logger.info(f"Created bridge: {bridge_id}")
        return bridge_id
    
    async def add_channel_to_bridge(self, bridge_id: str, channel_id: str):
        """Add a channel to a bridge"""
        await self._api_call(
            "POST",
            f"bridges/{bridge_id}/addChannel",
            params={"channel": channel_id}
        )
        logger.info(f"Added channel {channel_id} to bridge {bridge_id}")
    
    async def remove_channel_from_bridge(self, bridge_id: str, channel_id: str):
        """Remove a channel from a bridge"""
        await self._api_call(
            "POST",
            f"bridges/{bridge_id}/removeChannel",
            params={"channel": channel_id}
        )
    
    async def destroy_bridge(self, bridge_id: str):
        """Destroy a bridge"""
        await self._api_call("DELETE", f"bridges/{bridge_id}")
        if bridge_id in self.bridges:
            del self.bridges[bridge_id]
        logger.info(f"Destroyed bridge: {bridge_id}")
    
    async def play_media(self, channel_id: str, media: str):
        """Play media on a channel"""
        await self._api_call(
            "POST",
            f"channels/{channel_id}/play",
            params={"media": media}
        )
    
    async def start_recording(
        self,
        channel_id: str,
        name: str,
        format: str = "wav"
    ) -> Optional[str]:
        """Start recording a channel"""
        result = await self._api_call(
            "POST",
            f"channels/{channel_id}/record",
            params={
                "name": name,
                "format": format,
                "ifExists": "overwrite"
            }
        )
        recording_name = result.get("name") if result else None
        logger.info(f"Started recording: {recording_name}")
        return recording_name
    
    async def stop_recording(self, recording_name: str):
        """Stop a recording"""
        await self._api_call("POST", f"recordings/live/{recording_name}/stop")
        logger.info(f"Stopped recording: {recording_name}")
    
    async def transfer_call(self, channel_id: str, destination: str):
        """Transfer a call to another destination"""
        # Create new channel to destination
        new_channel_id = await self.originate_call(destination)
        
        # Create bridge and add both channels
        bridge_id = await self.create_bridge()
        await self.add_channel_to_bridge(bridge_id, channel_id)
        await self.add_channel_to_bridge(bridge_id, new_channel_id)
        
        logger.info(f"Transferred call {channel_id} to {destination}")
        return new_channel_id
    
    async def send_audio(self, channel_id: str, audio_bytes: bytes):
        """
        Send audio to a channel
        Note: This requires external media application setup
        """
        # In production, this would stream audio via RTP
        # For now, we log the attempt
        logger.debug(f"Would send {len(audio_bytes)} bytes to {channel_id}")
    
    async def get_channel_variable(self, channel_id: str, variable: str) -> Optional[str]:
        """Get a channel variable"""
        result = await self._api_call(
            "GET",
            f"channels/{channel_id}/variable",
            params={"variable": variable}
        )
        return result.get("value") if result else None
    
    async def set_channel_variable(self, channel_id: str, variable: str, value: str):
        """Set a channel variable"""
        await self._api_call(
            "POST",
            f"channels/{channel_id}/variable",
            params={"variable": variable, "value": value}
        )
    
    async def disconnect(self):
        """Disconnect from ARI"""
        if self.websocket:
            await self.websocket.close()
        if self.session:
            await self.session.close()
        self.is_connected = False
        logger.info("Disconnected from Asterisk ARI")
