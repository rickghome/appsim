"""Message broker for simulation events."""
import asyncio
from typing import Dict, Any, Set, Callable, Coroutine
from datetime import datetime

class MessageBrokerClient:
    """Client for subscribing to message broker channels."""
    
    def __init__(self):
        self._subscriptions: Dict[str, Callable] = {}
        self._message_queue = asyncio.Queue()
        self._running = True
        self._message_task = None
        self.app = None
        
    def subscribe_to_channel(self, channel: str, callback: Callable) -> None:
        """Subscribe to a message channel with a callback."""
        print(f"Subscribing to channel {channel}")
        self._subscriptions[channel] = callback
        
    def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from a message channel."""
        self._subscriptions.pop(channel, None)
        
    async def publish_message(self, channel: str, message: Dict[str, Any]) -> None:
        """Publish a message to a channel."""
        message["timestamp"] = datetime.now().isoformat()
        message["channel"] = channel
        await self._message_queue.put(message)
        
    async def get_message(self) -> Dict[str, Any]:
        """Get the next message from the queue."""
        return await self._message_queue.get()
        
    def get_subscriptions(self) -> Set[str]:
        """Get the set of subscribed channels."""
        return set(self._subscriptions.keys())
        
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle an incoming message by calling the appropriate callback."""
        try:
            channel = message.get("channel")
            if channel in self._subscriptions:
                callback = self._subscriptions[channel]
                await callback(message)
        except Exception as e:
            print(f"Error handling message: {e}")
            
    async def start(self) -> None:
        """Start processing messages."""
        if not self._message_task:
            self._running = True
            self._message_task = asyncio.create_task(self._process_messages())
            
    async def stop(self) -> None:
        """Stop processing messages."""
        self._running = False
        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
            self._message_task = None
            
    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self._running:
            try:
                message = await self._message_queue.get()
                await self.handle_message(message)
                self._message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing message: {e}")
                continue
