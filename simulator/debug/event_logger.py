"""Event logger that captures and displays events in the terminal."""
import logging
from datetime import datetime
from typing import Any, Dict
from ..core.providers import ServiceProvider, ServiceProviderState
from ..core.observer import Observer

class EventLogger(ServiceProvider, Observer):
    """A simple event logger that displays events in the terminal."""
    
    def __init__(self):
        """Initialize the event logger."""
        ServiceProvider.__init__(self, "event_logger")
        Observer.__init__(self)
        self.events = []
        
    def update(self, subject: Any, event_type: str, data: Dict[str, Any] = None):
        """Handle an update from a subject."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        subject_name = getattr(subject, 'name', str(subject))
        
        # Format the event message
        if event_type == "state_change":
            old_state = data.get('old_state', 'unknown')
            new_state = data.get('new_state', 'unknown')
            message = f"[{timestamp}] {subject_name}: State changed from {old_state} to {new_state}"
            
            # Print summary when transitioning to DIDRUN
            if new_state == "DIDRUN":
                print("\n=== Event Summary ===")
                print(f"Total events captured: {len(self.events)}")
                for event in self.events:
                    if event['event_type'] != 'state_change':  # Skip state changes to avoid noise
                        print(f"[{event['timestamp']}] {event['subject']}: {event['event_type']} - {event['data']}")
                print("===================\n")
                
        elif event_type == "job_complete":
            job = data.get('job')
            status = "succeeded" if job and job.state == "DONE" else "failed"
            message = f"[{timestamp}] {subject_name}: Job {job.id if job else 'unknown'} {status}"
        else:
            message = f"[{timestamp}] {subject_name}: {event_type} - {data}"
            
        print(message)
        self.events.append({
            'timestamp': timestamp,
            'subject': subject_name,
            'event_type': event_type,
            'data': data
        })
        
    async def handle_event(self, event):
        """Handle events from the service provider."""
        # We don't need to do anything here since we're just observing
        pass
        
    async def start(self):
        """Start the event logger."""
        print("\n=== Event Logger Started ===\n")
        await super().start()
        
    async def stop(self):
        """Stop the event logger."""
        await super().stop()
        print("\n=== Event Logger Stopped ===")
        print(f"Total events captured: {len(self.events)}\n")
