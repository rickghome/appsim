from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from ..core import Event

@dataclass
class EventRecord:
    """A record of a simulation event with metadata."""
    timestamp: datetime
    event_type: str
    source: str
    data: Dict[str, Any]
    component_id: Optional[str] = None
    state_before: Optional[str] = None
    state_after: Optional[str] = None

class EventStore:
    """Stores and indexes simulation events for debugging."""
    
    def __init__(self):
        self.events: List[EventRecord] = []
        self.component_states: Dict[str, str] = {}  # Current state of each component
        self.component_history: Dict[str, List[EventRecord]] = {}  # State history by component
        
    def store_event(self, event: Event):
        """Store an event and update component state tracking."""
        record = EventRecord(
            timestamp=datetime.now(),
            event_type=event.type,
            source=event.source,
            data=event.data,
            component_id=event.data.get('component_id'),
            state_before=event.data.get('state_before'),
            state_after=event.data.get('state_after')
        )
        
        # Store the event
        self.events.append(record)
        
        # Update component state if this is a state change
        if record.component_id and record.state_after:
            self.component_states[record.component_id] = record.state_after
            
            # Add to component history
            if record.component_id not in self.component_history:
                self.component_history[record.component_id] = []
            self.component_history[record.component_id].append(record)
            
    def get_events(self, start_time: Optional[datetime] = None, 
                  end_time: Optional[datetime] = None,
                  event_types: Optional[List[str]] = None,
                  component_id: Optional[str] = None) -> List[EventRecord]:
        """Query events with optional filters."""
        filtered = self.events
        
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        if event_types:
            filtered = [e for e in filtered if e.event_type in event_types]
        if component_id:
            filtered = [e for e in filtered if e.component_id == component_id]
            
        return filtered
        
    def get_component_state(self, component_id: str) -> Optional[str]:
        """Get the current state of a component."""
        return self.component_states.get(component_id)
        
    def get_component_history(self, component_id: str) -> List[EventRecord]:
        """Get the state change history for a component."""
        return self.component_history.get(component_id, [])
