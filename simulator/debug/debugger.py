from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
from enum import Enum

from ..core import ServiceProvider, Event, Observer, SimulationObserver, Stateful
from .event_store import EventStore
from ..core.message_broker import MessageBrokerClient

class DebuggerState(Enum):
    """States for the debugger."""
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STEPPING = "STEPPING"

class Debugger(ServiceProvider, MessageBrokerClient, Observer, Stateful):
    """Debug service that captures and analyzes simulation events.
    
    Features:
    - Event capture and persistence
    - Component state tracking
    - Timeline visualization
    - State transition analysis
    """
    
    def __init__(self, name: str = "debugger"):
        # Initialize parent classes
        ServiceProvider.__init__(self, name)
        MessageBrokerClient.__init__(self)
        Observer.__init__(self)
        Stateful.__init__(self, DebuggerState.STOPPED.value)
        
        self.event_store = EventStore()
        self._paused = False
        self._step_condition = asyncio.Condition()
        self._breakpoints: Dict[str, Dict[str, Any]] = {}  # Breakpoints by component_id
        
        # Create UI but don't start it yet
        from .debug_ui import SimpleDebuggerUI
        self.ui = SimpleDebuggerUI(self)
        self._ui_started = False
        
        # Subscribe to state changes
        self.subscribe_to_channel("state_change", self.handle_event)
        
    def _start_ui(self):
        """Start the debugger UI asynchronously."""
        try:
            # Run UI in a separate task to not block
            asyncio.create_task(self.ui.run())
        except Exception as e:
            print(f"Failed to start debugger UI: {e}")
            
    async def start(self):
        """Start the debugger service."""
        # Start parent service provider
        await super().start()  # Ensure parent start is called
        
        # Start message broker client
        await MessageBrokerClient.start(self)
        
        # Start UI if not already started
        if not self._ui_started:
            await self._start_ui()
            self._ui_started = True
            
        self.transition_to(DebuggerState.RUNNING.value)
        
    def can_transition(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        transitions = {
            "IDLE": {DebuggerState.STOPPED.value, "WILLRUN"},
            DebuggerState.STOPPED.value: {DebuggerState.RUNNING.value, "WILLRUN"},
            DebuggerState.RUNNING.value: {DebuggerState.PAUSED.value, DebuggerState.STOPPED.value, "DIDRUN"},
            DebuggerState.PAUSED.value: {DebuggerState.RUNNING.value, DebuggerState.STEPPING.value},
            DebuggerState.STEPPING.value: {DebuggerState.PAUSED.value, DebuggerState.RUNNING.value},
            "WILLRUN": {"RUNNING", "DIDRUN"},
            "DIDRUN": {"DONE"},
            "DONE": {"IDLE"}
        }
        return new_state in transitions.get(self.state, set())
        
    async def stop(self):
        """Stop the debugger service."""
        if self.can_transition(DebuggerState.STOPPED.value):
            self.transition_to(DebuggerState.STOPPED.value)
            
    async def handle_event(self, event: Event) -> None:
        """Handle an incoming simulation event."""
        try:
            # Store the event
            self.event_store.store_event(event)
            
            # Update UI with event info
            event_type = event.type
            if event_type == "state_change":
                component_id = event.data.get("component_id", "unknown")
                old_state = event.data.get("old_state", "unknown")
                new_state = event.data.get("new_state", "unknown")
                if self._ui_started:
                    self.ui.update_state(component_id, new_state)
                    self.ui.log_event(f"State change: {component_id} {old_state} -> {new_state}")
            elif event_type == "job_complete":
                job_id = event.data.get("job_id", "unknown")
                final_state = event.data.get("final_state", "unknown")
                if self._ui_started:
                    self.ui.log_event(f"Job {job_id} completed with state {final_state}")
            
            # Check breakpoints
            if self._should_break(event):
                await self._handle_breakpoint(event)
                
        except Exception as e:
            print(f"Error handling debug event: {e}")
            
    def _should_break(self, event: Event) -> bool:
        """Check if we should break on this event."""
        component_id = event.data.get('component_id')
        if not component_id or component_id not in self._breakpoints:
            return False
            
        breakpoint = self._breakpoints[component_id]
        if 'state' in breakpoint and event.data.get('state_after') == breakpoint['state']:
            return True
        if 'event_type' in breakpoint and event.type == breakpoint['event_type']:
            return True
            
        return False
        
    async def _handle_breakpoint(self, event: Event):
        """Handle a breakpoint being hit."""
        self._paused = True
        # Wait for resume or step command
        async with self._step_condition:
            await self._step_condition.wait()
            
    async def pause(self):
        """Pause the simulation."""
        if self.can_transition(DebuggerState.PAUSED.value):
            self.transition_to(DebuggerState.PAUSED.value)
            
    async def step(self):
        """Execute one step when paused."""
        if self.can_transition(DebuggerState.STEPPING.value):
            self.transition_to(DebuggerState.STEPPING.value)
            # Process one event
            self.transition_to(DebuggerState.PAUSED.value)
            
    async def resume(self):
        """Resume the simulation."""
        if self.can_transition(DebuggerState.RUNNING.value):
            self.transition_to(DebuggerState.RUNNING.value)
            
    def set_breakpoint(self, component_id: str, **conditions):
        """Set a breakpoint for a component with conditions."""
        self._breakpoints[component_id] = conditions
        
    def clear_breakpoint(self, component_id: str):
        """Clear breakpoints for a component."""
        if component_id in self._breakpoints:
            del self._breakpoints[component_id]
            
    def get_timeline(self, start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get timeline of events."""
        events = self.event_store.get_events(start_time, end_time)
        return [{'timestamp': e.timestamp,
                'type': e.event_type,
                'source': e.source,
                'data': e.data} for e in events]
                
    def get_component_state(self, component_id: str) -> Optional[str]:
        """Get current state of a component."""
        return self.event_store.get_component_state(component_id)
        
    def get_component_history(self, component_id: str) -> List[Dict[str, Any]]:
        """Get state change history for a component."""
        events = self.event_store.get_component_history(component_id)
        return [{'timestamp': e.timestamp,
                'state_before': e.state_before,
                'state_after': e.state_after,
                'data': e.data} for e in events]

    async def on_event(self, event: Event):
        """Handle synchronous events from Stateful objects."""
        # Convert to async and store
        asyncio.create_task(self.handle_event(event))

    def on_state_change(self, component_id: str, old_state: str, new_state: str) -> None:
        """Handle state changes."""
        try:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")
            event_str = f"{timestamp} {component_id} state: {old_state} -> {new_state}"
            print(f"DEBUG: Recording state change: {event_str}")  # Debug log
            if self.ui:
                print(f"DEBUG: Updating UI with state change")  # Debug log
                self.ui.log_event(event_str)
                self.ui.update_state(component_id, new_state)
            else:
                print("DEBUG: UI not available")  # Debug log
        except Exception as e:
            print(f"DEBUG: Error in on_state_change: {e}")  # Debug log

    def on_state_changed(self, component: Any, event_data: Dict[str, Any]):
        """Handle state change events from observed components."""
        try:
            old_state = event_data.get('old_state')
            new_state = event_data.get('new_state')
            
            self.on_state_change(component.__class__.__name__, old_state, new_state)
            
            # Create and store event asynchronously
            event = Event(
                type="state_change",
                source=component.__class__.__name__,
                data=event_data
            )
            asyncio.create_task(self.handle_event(event))
        except Exception as e:
            print(f"Error handling state change: {e}")

    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle a message from the message broker."""
        try:
            event_type = message.get("type", "unknown")
            if event_type == "state_change":
                component_id = message.get("component_id", "unknown")
                old_state = message.get("old_state", "unknown")
                new_state = message.get("new_state", "unknown")
                if self._ui_started:
                    self.ui.update_state(component_id, new_state)
                    self.ui.log_event(f"State change: {component_id} {old_state} -> {new_state}")
            elif event_type == "job_complete":
                job_id = message.get("job_id", "unknown")
                final_state = message.get("final_state", "unknown")
                if self._ui_started:
                    self.ui.log_event(f"Job {job_id} completed with state {final_state}")
        except Exception as e:
            print(f"Error handling message: {e}")
