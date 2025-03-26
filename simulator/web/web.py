"""Web server implementation."""
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from ..core import ServiceProvider
from .types import HttpRequest, HttpResponse
from .form import Form, FormState

@dataclass
class Request:
    """A web request."""
    path: str
    verb: str
    data: Dict[str, Any]

class WebServer(ServiceProvider):
    """A web server that can handle HTTP-like requests."""
    
    def __init__(self, name: str):
        """Initialize the web server."""
        super().__init__(name)
        self.forms: Dict[str, Form] = {}
        self.routes: Dict[str, Dict[str, Callable]] = {}
        
    def add_form(self, path: str, verb: str, form: Form) -> None:
        """Add a form at a path."""
        form.app = self.app  # Pass app reference to form
        self.forms[path] = form
        
    def get_form(self, path: str, verb: str = None) -> Optional[Form]:
        """Get a form at a path."""
        return self.forms.get(path)
        
    def register_route(self, path: str, verb: str, handler: Callable) -> None:
        """Register a route handler."""
        if path not in self.routes:
            self.routes[path] = {}
        self.routes[path][verb] = handler
        
    def handle_request(self, path: str, verb: str, request: HttpRequest) -> HttpResponse:
        """Handle an incoming HTTP request."""
        # Check for custom route handler first
        if path in self.routes and verb in self.routes[path]:
            return self.routes[path][verb](request)
            
        # Fall back to form handling
        form = self.forms.get(path)
        if not form:
            return HttpResponse(404, {"error": f"No form registered at path: {path}"})
            
        if verb == "GET":
            if form.state == "FILLED":
                return HttpResponse(200, form.data)
            return HttpResponse(200, {})
        elif verb == "POST":
            form.fill(request.data)
            return HttpResponse(200, form.data)
        else:
            return HttpResponse(400, {"error": f"Unsupported verb: {verb}"})
            
    def clear_form(self, path: str) -> None:
        """Clear a form at a path."""
        form = self.forms.get(path)
        if not form:
            raise ValueError(f"No form registered at path: {path}")
        form.clear()
