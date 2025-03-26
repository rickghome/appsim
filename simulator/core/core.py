from enum import Enum
from datetime import datetime
from typing import Set, Dict, Callable, Tuple, List, Optional, Any
from abc import ABC, abstractmethod

class Event:
    def __init__(self, type: str, source: Any, data: Dict[str, Any]):
        self.type = type
        self.source = source
        self.source_id = getattr(source, 'id', None)
        self.data = data
        self.timestamp = datetime.now()

class SimulationObserver:
    """Base class for observing simulation events."""
    def on_event(self, event: Event):
        pass

class EventObserver:
    def on_event(self, event: Event):
        pass

class Observer(ABC):
    """Abstract base class for observers of simulation events."""
    @abstractmethod
    async def handle_event(self, event: Event):
        """Handle an event."""
        pass

class Stateful:
    """Base class for objects with state."""
    def __init__(self, initial_state: str):
        """Initialize with given state."""
        self._state = initial_state
        self.state_history: List[Tuple[datetime, str]] = [(datetime.now(), self._state)]
        self.callbacks: Set[Callable[[str, str], None]] = set()
        self._observers: List[SimulationObserver] = []
        
    @property
    def state(self) -> str:
        """Get the current state."""
        return self._state
        
    @state.setter
    def state(self, new_state: str):
        """Set the state."""
        self._state = new_state
            
    def can_transition(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        return True  # Base class allows all transitions
        
    def transition_to(self, new_state: str) -> bool:
        """Transition to a new state if valid."""
        if self.can_transition(new_state):
            old_state = self.state
            self.state = new_state
            self.state_history.append((datetime.now(), new_state))
            
            # Notify observers
            event = Event(
                type="state_changed",
                source=self,
                data={
                    "old_state": old_state,
                    "new_state": new_state,
                    "old_state_name": old_state,
                    "new_state_name": new_state,
                    "object_type": self.__class__.__name__,
                    "object_id": getattr(self, 'id', None)
                }
            )
            
            # Emit the event
            for observer in self._observers:
                observer.on_event(event)
                
            # Call registered callbacks
            for callback in self.callbacks:
                callback(old_state, new_state)
                
            return True
        return False

    def add_observer(self, observer: SimulationObserver):
        """Add an observer to receive simulation events."""
        if observer not in self._observers:
            self._observers.append(observer)
            
    def remove_observer(self, observer: SimulationObserver):
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def register_callback(self, callback: Callable[[str, str], None]):
        """Register a callback for state transitions."""
        self.callbacks.add(callback)

    def is_terminal(self) -> bool:
        """Check if the current state is terminal."""
        return False  # Base class does not have terminal states

class StatefulEnum(Stateful):
    """Base class for state-driven objects."""
    VALID_TRANSITIONS: Dict[str, Set[str]]
    
    def __init__(self, initial_state):
        """Initialize with given state."""
        if not hasattr(self, 'VALID_TRANSITIONS'):
            raise ValueError(f"{self.__class__.__name__} must define VALID_TRANSITIONS")
            
        # Convert initial state to string if it's an enum
        initial_state_str = initial_state.value if isinstance(initial_state, Enum) else initial_state
        
        # Convert all transitions to use string values
        self.VALID_TRANSITIONS = {
            k.value if isinstance(k, Enum) else k: {
                v.value if isinstance(v, Enum) else v for v in values
            }
            for k, values in self.VALID_TRANSITIONS.items()
        }
        
        if initial_state_str not in self.VALID_TRANSITIONS:
            raise ValueError(f"Invalid initial state {initial_state_str}. Valid states: {list(self.VALID_TRANSITIONS.keys())}")
        super().__init__(initial_state_str)
        
    def can_transition(self, new_state) -> bool:
        """Check if transition to new_state is valid from current state."""
        new_state_str = new_state.value if isinstance(new_state, Enum) else new_state
        return new_state_str in self.VALID_TRANSITIONS[self.state]
        
    @property
    def state(self):
        """Get the current state."""
        return self._state
        
    @state.setter
    def state(self, new_state):
        """Set the state."""
        # Convert enum to string if needed
        new_state_str = new_state.value if isinstance(new_state, Enum) else new_state
        if self.can_transition(new_state_str):
            old_state = self._state
            self._state = new_state_str
            self.state_history.append((datetime.now(), new_state_str))
            for callback in self.callbacks:
                callback(old_state, new_state_str)
        else:
            raise ValueError(f"Invalid transition for {self.__class__.__name__} from {self._state} to {new_state_str}")