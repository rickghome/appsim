"""State management utilities."""
from enum import Enum
from typing import Set, Dict, Callable, Tuple, List, Any
from datetime import datetime

class Event:
    """Base class for simulation events."""
    def __init__(self, type: str, source: Any, data: Dict[str, Any]):
        self.type = type
        self.source = source
        self.source_id = getattr(source, 'id', None)
        self.data = data
        self.timestamp = datetime.now()

class Stateful:
    """Base class for objects with state."""
    def __init__(self, initial_state: str):
        """Initialize with given state."""
        self._state = initial_state
        self.state_history: List[Tuple[datetime, str]] = [(datetime.now(), self._state)]
        self.callbacks: Set[Callable[[str, str], None]] = set()
        
    @property
    def state(self) -> str:
        """Get the current state."""
        return self._state
        
    @state.setter
    def state(self, new_state: str):
        """Set the state."""
        if self.can_transition(new_state):
            old_state = self._state
            self._state = new_state
            self.state_history.append((datetime.now(), new_state))
            for callback in self.callbacks:
                callback(old_state, new_state)
        else:
            raise ValueError(f"Invalid transition from {self._state} to {new_state}")
            
    def can_transition(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        return True  # Base class allows all transitions

class StatefulEnum(Enum):
    """Base class for state enums with transition validation."""
    
    @classmethod
    def get_valid_transitions(cls, current_state: str) -> Set[str]:
        """Get valid transitions from a state."""
        # By default, allow transitions to any other state
        return {state.value for state in cls}
        
    @classmethod
    def validate_transition(cls, from_state: str, to_state: str) -> bool:
        """Validate a state transition."""
        if not from_state or not to_state:
            return False
            
        valid_transitions = cls.get_valid_transitions(from_state)
        return to_state in valid_transitions
