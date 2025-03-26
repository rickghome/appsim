"""
Defines core actor abstractions for the simulation system.

Actors are the fundamental building blocks of the simulation that can:
- Receive and process messages
- Maintain internal state
- Communicate with other actors through their container
- Participate in the simulation lifecycle
"""
import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Set
from .state import Stateful
from .providers import ServiceProvider

class ActorState(Enum):
    """Represents the possible states of an actor."""
    IDLE = "IDLE"
    WILLRUN = "WILLRUN"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DIDRUN = "DIDRUN"
    DONE = "DONE"
    ERROR = "ERROR"

class Actor(Stateful, ABC):
    """Base class for sim actors, who run continuously (unlike jobs)."""
    
    VALID_TRANSITIONS = {
        ActorState.IDLE.value: {ActorState.WILLRUN.value, ActorState.ERROR.value},
        ActorState.WILLRUN.value: {ActorState.RUNNING.value, ActorState.ERROR.value},
        ActorState.RUNNING.value: {ActorState.PAUSED.value, ActorState.DIDRUN.value, ActorState.ERROR.value},
        ActorState.PAUSED.value: {ActorState.RUNNING.value, ActorState.ERROR.value},
        ActorState.DIDRUN.value: {ActorState.DONE.value, ActorState.ERROR.value},
        ActorState.DONE.value: {ActorState.IDLE.value},
        ActorState.ERROR.value: {ActorState.IDLE.value}
    }
    
    def __init__(self, actor_id: str, container: ServiceProvider):
        """Initialize the actor with its container ServiceProvider."""
        Stateful.__init__(self, ActorState.IDLE.value)
        self.actor_id = actor_id
        self.container = container
        self._context: Dict[str, Any] = {}
        self._message_queue = asyncio.Queue()  # Local queue for received messages
        
        # Register with container for message handling
        self.container.add_observer(self)
        
    @property
    def context(self) -> Dict[str, Any]:
        """Returns the actor's context dictionary."""
        return self._context

    async def send_message(self, message: Any) -> None:
        """Sends a message through the container."""
        await self.container.publish_message({
            "type": "actor_message",
            "source_id": self.actor_id,
            "content": message
        })

    async def on_message(self, provider_name: str, message: Any) -> None:
        """Handle messages from container. Only process messages targeted at this actor."""
        if isinstance(message, dict) and message.get("type") == "actor_message":
            if message.get("target_id") == self.actor_id:
                await self._message_queue.put(message["content"])

    async def receive_message(self) -> Any:
        """Receives the next message from the actor's queue."""
        return await self._message_queue.get()

    @abstractmethod
    async def handle_message(self, message: Any) -> None:
        """Handle an incoming message."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the actor."""
        self.transition(ActorState.WILLRUN.value)

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up resources and prepare for shutdown."""
        # Unregister from container
        self.container.remove_observer(self)
        self.transition(ActorState.DIDRUN.value)

    async def run(self) -> None:
        """Main actor loop."""
        try:
            await self.initialize()
            self.transition(ActorState.RUNNING.value)
            
            while self.state == ActorState.RUNNING.value:
                message = await self.receive_message()
                await self.handle_message(message)
                
        except Exception as e:
            self.transition(ActorState.ERROR.value)
            raise
        finally:
            await self.shutdown()
            self.transition(ActorState.DONE.value)
