"""Common types for web module."""
from enum import Enum
from typing import Dict, Any

class HttpVerb(Enum):
    """HTTP verbs supported by the web server."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class HttpRequest:
    """A simple HTTP request object."""
    def __init__(self, verb: str, path: str, data: Dict[str, Any] = None):
        self.verb = verb
        self.path = path
        self.data = data or {}

class HttpResponse:
    """A simple HTTP response object."""
    def __init__(self, status: int, data: Dict[str, Any]):
        self.status = status
        self.data = data
        
    @classmethod
    def ok(cls, data: Dict[str, Any]):
        """Create 200 OK response"""
        return cls(200, data)
        
    @classmethod
    def created(cls, data: Dict[str, Any]):
        """Create 201 Created response"""
        return cls(201, data)
        
    @classmethod
    def bad_request(cls, message: str):
        """Create 400 Bad Request response"""
        return cls(400, {"error": message})
        
    @classmethod
    def not_found(cls, message: str):
        """Create 404 Not Found response"""
        return cls(404, {"error": message})
        
    @classmethod
    def server_error(cls, data: Dict[str, Any]):
        """Create 500 Server Error response"""
        return cls(500, data)
