import asyncio
import json
import websockets
from typing import Dict, List, Callable, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BinanceWebSocketManager:
    def __init__(self):
        self.base_url = "wss://fstream.binance.com"
        self.spot_url = "wss://stream.binance.com:9443"
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.running = False
        
    async def connect(self, stream_name: str, callback: Callable, is_futures: bool = True):
        """Connect to a Binance WebSocket stream"""
        url = f"{self.base_url}/ws/{stream_name}" if is_futures else f"{self.spot_url}/ws/{stream_name}"
        
        logger.info(f"Attempting to connect to WebSocket: {url}")
        
        if stream_name not in self.callbacks:
            self.callbacks[stream_name] = []
        self.callbacks[stream_name].append(callback)
        
        try:
            websocket = await websockets.connect(url)
            self.connections[stream_name] = websocket
            logger.info(f"Successfully connected to {stream_name}")
            
            asyncio.create_task(self._handle_messages(stream_name, websocket))
            
        except Exception as e:
            logger.error(f"Failed to connect to {stream_name}: {e}", exc_info=True)
            raise
            
    async def _handle_messages(self, stream_name: str, websocket: websockets.WebSocketClientProtocol):
        """Handle incoming messages from a WebSocket stream"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Debug logging for liquidation stream
                    if "forceOrder" in stream_name:
                        logger.info(f"Received message on {stream_name}: {message[:200]}...")
                    for callback in self.callbacks.get(stream_name, []):
                        await callback(data)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode message from {stream_name}: {message}")
                except Exception as e:
                    logger.error(f"Error processing message from {stream_name}: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Connection closed for {stream_name}")
            await self._reconnect(stream_name)
        except Exception as e:
            logger.error(f"Unexpected error in message handler for {stream_name}: {e}")
            
    async def _reconnect(self, stream_name: str):
        """Reconnect to a stream after disconnection"""
        await asyncio.sleep(5)  # Wait before reconnecting
        
        if stream_name in self.connections:
            del self.connections[stream_name]
            
        if stream_name in self.callbacks and self.callbacks[stream_name]:
            is_futures = "fstream" in stream_name or "@forceOrder" in stream_name
            await self.connect(stream_name, self.callbacks[stream_name][0], is_futures)
            
    async def subscribe_multiple(self, subscriptions: List[Dict]):
        """Subscribe to multiple streams at once"""
        tasks = []
        for sub in subscriptions:
            task = self.connect(sub['stream'], sub['callback'], sub.get('is_futures', True))
            tasks.append(task)
        await asyncio.gather(*tasks)
        
    async def close_all(self):
        """Close all WebSocket connections"""
        for stream_name, websocket in self.connections.items():
            await websocket.close()
        self.connections.clear()
        self.callbacks.clear()