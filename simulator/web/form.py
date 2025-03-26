"""Form management for web requests."""
from enum import Enum
from typing import Dict, List, Set, Any
from faker import Faker
from datetime import datetime
from ..core import Stateful, Event, SimulationObserver

class FieldType(Enum):
    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"

class FormState(Enum):
    """States that a form can be in"""
    EMPTY = "empty"      # Initial state, no data filled
    FILLED = "filled"    # Form has been filled with data

class Field:
    """A form field with type information"""
    def __init__(self, name: str, field_type: 'FieldType'):
        self.name = name
        self.field_type = field_type
        self.required = True
        self.options: List[str] = []
        
    def optional(self) -> 'Field':
        """Mark field as optional"""
        self.required = False
        return self

class Form(Stateful):
    """A form that can be filled with data."""
    
    def __init__(self, path: str, verb: str):
        """Initialize a form."""
        super().__init__(FormState.EMPTY.value)
        self.name = f"{verb} {path}"
        self.path = path
        self.verb = verb
        self.fields: Dict[str, Dict[str, Any]] = {}
        self.required_fields: Set[str] = set()
        self.faker = Faker()
        self.data: Dict[str, Any] = {}
        
    def can_transition(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        # Allow any transition between EMPTY and FILLED
        return new_state in {FormState.EMPTY.value, FormState.FILLED.value}
        
    def text(self, name: str, label: str = None) -> 'Form':
        """Add a text field to the form."""
        self.fields[name] = {"type": FieldType.TEXT.value, "label": label or name}
        self.required_fields.add(name)
        return self
        
    def number(self, name: str, label: str = None) -> 'Form':
        """Add a number field to the form."""
        self.fields[name] = {"type": FieldType.NUMBER.value, "label": label or name}
        self.required_fields.add(name)
        return self
        
    def select(self, name: str, options: List[str], label: str = None) -> 'Form':
        """Add a select field to the form."""
        self.fields[name] = {
            "type": FieldType.SELECT.value,
            "label": label or name,
            "options": options
        }
        self.required_fields.add(name)
        return self
        
    def optional(self, name: str) -> 'Form':
        """Mark a field as optional."""
        if name in self.required_fields:
            self.required_fields.remove(name)
        return self
        
    def fill(self, data: Dict[str, Any]) -> None:
        """Fill the form with data."""
        # Validate required fields
        missing = self.required_fields - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
            
        # Validate field types
        for name, value in data.items():
            if name not in self.fields:
                raise ValueError(f"Unknown field: {name}")
                
            field = self.fields[name]
            if field["type"] == FieldType.NUMBER.value:
                try:
                    data[name] = float(value)
                except ValueError:
                    raise ValueError(f"Field {name} must be a number")
                    
            elif field["type"] == FieldType.SELECT.value:
                if value not in field["options"]:
                    raise ValueError(f"Invalid option for {name}: {value}")
                    
        self.data = data
        self.state = FormState.FILLED.value
        
        # Emit event when form is filled
        if hasattr(self, 'app') and self.app:
            event = Event("form_filled", self, {
                "form_name": self.name,
                "path": self.path,
                "verb": self.verb,
                "data": self.data
            })
            self.app.message_broker.publish("state_change", event)
        
    def clear(self) -> None:
        """Clear the form data."""
        self.data = {}
        self.state = FormState.EMPTY.value
        
        # Emit event when form is cleared
        if hasattr(self, 'app') and self.app:
            event = Event("form_cleared", self, {
                "form_name": self.name,
                "path": self.path,
                "verb": self.verb
            })
            self.app.message_broker.publish("state_change", event)
