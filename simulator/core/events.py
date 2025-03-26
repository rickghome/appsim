from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from .core import SimulationObserver, Event
from ..web.rest import RESTServer
from ..web.types import HttpRequest, HttpResponse, HttpVerb

class SimulationEventService(RESTServer, SimulationObserver):
    """RESTful service that collects and exposes simulation events.
    
    Endpoints:
    - GET /events - Get all events (with optional filtering)
    - GET /events/types - Get available event types
    - GET /events/sources - Get active event sources
    - POST /events/filter - Set event filtering criteria
    """
    
    def __init__(self, name: str, app, max_events: int = 1000):
        RESTServer.__init__(self, name, app)
        self.events = deque(maxlen=max_events)
        self.filters = {}  # Type -> predicate mapping
        
    def on_event(self, event: Event):
        """Collect simulation events that match current filters."""
        if self._should_collect(event):
            self.events.append(event)
            
    def _should_collect(self, event: Event) -> bool:
        """Check if event matches current filters."""
        if not self.filters:
            return True
        
        filter_fn = self.filters.get(event.type)
        if not filter_fn:
            return True
            
        return self.matches_filter(event, filter_fn)
            
    def matches_filter(self, event: Event, filter_expr: str) -> bool:
        """Check if an event matches a filter expression."""
        try:
            # Create a context with event data
            context = {
                "type": event.type,
                "source_type": event.source.__class__.__name__,
                "source_id": getattr(event.source, 'id', None),
                "timestamp": event.timestamp,
                **event.data
            }
            
            # Add state names to the context
            if 'state' in event.data:
                context['state_name'] = event.source.state_name
            
            # Evaluate the filter expression
            return eval(filter_expr, {"__builtins__": {}}, context)
        except Exception as e:
            print(f"Error evaluating filter: {e}")
            return False
            
    async def get(self, path_parts: List[str], request: HttpRequest) -> HttpResponse:
        """Handle GET requests for events."""
        if not path_parts:
            # GET /events - Return all events
            return HttpResponse(200, {
                "events": [self._event_to_dict(e) for e in self.events]
            })
            
        subpath = path_parts[0]
        if subpath == "types":
            # GET /events/types - Return available event types
            return HttpResponse(200, {
                "types": ["state_changed", "process_started", "process_ended",
                         "resource_allocated", "resource_released",
                         "message_sent", "message_received",
                         "system_error", "system_ready"]
            })
            
        if subpath == "sources":
            # GET /events/sources - Return unique event sources
            sources = {e.source.__class__.__name__ for e in self.events}
            return HttpResponse(200, {"sources": list(sources)})
            
        return HttpResponse(404, {"error": "Not found"})
        
    async def store(self, path_parts: List[str], request: HttpRequest) -> HttpResponse:
        """Handle POST requests."""
        if not path_parts or path_parts[0] != "filter":
            return HttpResponse(404, {"error": "Not found"})
            
        # POST /events/filter - Set event filters
        try:
            filters = request.data.get("filters", {})
            self.filters = filters
            return HttpResponse(200, {"message": "Filters updated"})
        except Exception as e:
            return HttpResponse(400, {"error": str(e)})
            
    def _event_to_dict(self, event: Event) -> Dict[str, Any]:
        """Convert Event to dictionary for JSON serialization."""
        return {
            "type": event.type,
            "source": event.source.__class__.__name__,
            "source_id": event.source_id,
            "data": event.data,
            "timestamp": event.timestamp.isoformat()
        }
