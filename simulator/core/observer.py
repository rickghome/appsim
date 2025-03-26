"""Observer pattern implementation for simulation components."""
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional
from .state import Event

class Observable:
    """Base class for objects that can be observed."""
    
    def __init__(self):
        self._observers: List[Observer] = []
        
    def add_observer(self, observer: 'Observer') -> None:
        """Add an observer."""
        if observer not in self._observers:
            self._observers.append(observer)
            
    def remove_observer(self, observer: 'Observer') -> None:
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
            
    def notify_observers(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Notify all observers of an event."""
        for observer in self._observers:
            observer.update(self, event_type, data)

    async def notify_observers_async(self, event: Event) -> None:
        """Notify all observers of an event asynchronously."""
        for observer in self._observers:
            await observer.handle_event(event)

class Observer(ABC):
    """Base observer interface for simulation components."""
    
    @abstractmethod
    def update(self, subject: Any, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Handle an update from a subject."""
        pass
        
    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """Handle an event."""
        pass

class SimulationObserver(Observer):
    """Observer specifically for simulation events."""
    
    def update(self, subject: Any, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Handle an update from a subject."""
        # Default implementation does nothing
        pass
    
    async def handle_event(self, event: Event) -> None:
        """Handle a simulation event."""
        event_type = event.type
        if event_type == "state_change":
            await self.on_state_change(event)
        elif event_type == "job_complete":
            await self.on_job_complete(event)
            
    async def on_state_change(self, event: Event) -> None:
        """Handle state change events."""
        component_id = event.data.get("component_id", "unknown")
        old_state = event.data.get("old_state", "unknown")
        new_state = event.data.get("new_state", "unknown")
        print(f"State change: {component_id} {old_state} -> {new_state}")
        
    async def on_job_complete(self, event: Event) -> None:
        """Handle job complete events."""
        job_id = event.data.get("job_id", "unknown")
        status = event.data.get("status", "unknown")
        print(f"Job complete: {job_id} {status}")
