"""Service provider base class."""
from typing import Optional, Any, List, Dict, Set
import asyncio
from enum import Enum
import logging
from .state import Stateful
from .job import Job
from .observer import Observable

class ServiceProviderState(Enum):
    """Represents the possible states of a service provider."""
    IDLE = "IDLE"
    WILLRUN = "WILLRUN"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DIDRUN = "DIDRUN"
    DONE = "DONE"
    ERROR = "ERROR"

class ServiceProvider(Stateful, Observable):
    """Base class for service providers that manage their own event loop, message queue, and job handling."""
    _valid_transitions = {
        ServiceProviderState.IDLE.value: {ServiceProviderState.WILLRUN.value, ServiceProviderState.ERROR.value},
        ServiceProviderState.WILLRUN.value: {ServiceProviderState.RUNNING.value, ServiceProviderState.DIDRUN.value, ServiceProviderState.ERROR.value},
        ServiceProviderState.RUNNING.value: {ServiceProviderState.PAUSED.value, ServiceProviderState.DIDRUN.value, ServiceProviderState.ERROR.value},
        ServiceProviderState.PAUSED.value: {ServiceProviderState.RUNNING.value, ServiceProviderState.ERROR.value},
        ServiceProviderState.DIDRUN.value: {ServiceProviderState.DONE.value, ServiceProviderState.ERROR.value},
        ServiceProviderState.DONE.value: {ServiceProviderState.IDLE.value},
        ServiceProviderState.ERROR.value: {ServiceProviderState.IDLE.value}
    }
    
    def __init__(self, name: str):
        """Initialize the service provider."""
        Stateful.__init__(self, ServiceProviderState.IDLE.value)
        Observable.__init__(self)
        self.name = name
        self.app = None  # Will be set during registration
        self.message_queue = []
        self.jobs: Dict[str, Job] = {}
        self._current_job = None
        
        # Register state change callback
        self.callbacks.add(self._on_state_change)
        
    def _on_state_change(self, old_state: str, new_state: str):
        """Handle state changes."""
        self.notify_observers("state_change", {
            "old_state": old_state,
            "new_state": new_state
        })
        
    async def start(self):
        """Start the service provider."""
        # Only transition if not already in the target state
        if self.state != ServiceProviderState.WILLRUN.value:
            self.state = ServiceProviderState.WILLRUN.value
        await asyncio.sleep(0.1)  # Give time for state change to propagate
        
        if self.state != ServiceProviderState.RUNNING.value:
            self.state = ServiceProviderState.RUNNING.value
        await self._run_event_loop()
        
    async def stop(self):
        """Stop the service provider."""
        if self.state != ServiceProviderState.DIDRUN.value:
            self.state = ServiceProviderState.DIDRUN.value
        await asyncio.sleep(0.1)  # Give time for state change to propagate
        
        if self.state != ServiceProviderState.DONE.value:
            self.state = ServiceProviderState.DONE.value
        
    async def _run_event_loop(self):
        """Run the event loop."""
        pass  # Subclasses should implement this
        
    async def publish_message(self, message: Any):
        """Publish a message to this provider's queue."""
        self.message_queue.append(message)
        
    def can_transition(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        return new_state in self._valid_transitions.get(self.state, set())
