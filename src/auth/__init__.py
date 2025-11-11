"""Simplified authentication module for ServiceNow MCP Server."""

from .unified_auth import UnifiedAuth, get_auth, authenticate_request, require_scope
from .simple_middleware import SimpleAuthMiddleware, get_current_user, require_scope_simple
from .decorators import requires_scope, optional_auth

__all__ = [
    "UnifiedAuth",
    "get_auth",
    "authenticate_request", 
    "require_scope",
    "SimpleAuthMiddleware",
    "get_current_user",
    "require_scope_simple",
    "requires_scope",
    "optional_auth"
]