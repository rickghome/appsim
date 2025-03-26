from typing import List, Dict, Any
from ..core import ServiceProvider, Command
from .types import HttpRequest, HttpResponse, HttpVerb
from .web import WebServer

class RESTServer(WebServer):
    """Base class for RESTful web servers.
    
    Implements standard CRUD operations mapped to HTTP verbs:
    - POST   -> store()  -> Create
    - GET    -> get()    -> Read
    - PUT    -> update() -> Update
    - DELETE -> delete() -> Delete
    """
    def __init__(self, name: str, app=None):
        super().__init__(name, app)
        
    def store(self, request: HttpRequest) -> HttpResponse:
        """Store a new resource"""
        return HttpResponse.created({"message": "Created"})
        
    def get(self, request: HttpRequest) -> HttpResponse:
        """Get a resource"""
        return HttpResponse.ok({"message": "Retrieved"})
        
    def update(self, request: HttpRequest) -> HttpResponse:
        """Update a resource"""
        return HttpResponse.ok({"message": "Updated"})
        
    def delete(self, request: HttpRequest) -> HttpResponse:
        """Delete a resource"""
        return HttpResponse.ok({"message": "Deleted"})
        
    def handle_request(self, path: str, verb: str, request: HttpRequest) -> HttpResponse:
        """Handle an incoming HTTP request"""
        try:
            if verb == HttpVerb.POST.value:
                return self.store(request)
            elif verb == HttpVerb.GET.value:
                return self.get(request)
            elif verb == HttpVerb.PUT.value:
                return self.update(request)
            elif verb == HttpVerb.DELETE.value:
                return self.delete(request)
            else:
                return HttpResponse.bad_request(f"Unsupported HTTP verb: {verb}")
        except Exception as e:
            return HttpResponse.server_error({"error": str(e)})
