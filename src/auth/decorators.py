"""Simple authentication decorators for MCP handlers."""

import functools
import logging
from typing import Callable, Any

from .simple_middleware import require_scope_simple

logger = logging.getLogger(__name__)


def requires_scope(scope: str):
    """Decorator to require specific scope for MCP tool handlers.
    
    Usage:
        @requires_scope("servicenow.incident.read")
        async def get_incident(incident_number: str) -> str:
            # Handler implementation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Check scope
            user_info = require_scope_simple(scope)
            
            # Log access
            user = user_info.get("user", "unknown")
            logger.info(f"User '{user}' accessing {func.__name__} with scope '{scope}'")
            
            # Call original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def optional_auth(func: Callable) -> Callable:
    """Decorator for handlers that work with or without authentication."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        from .simple_middleware import get_current_user
        
        user_info = get_current_user()
        if user_info and user_info["authenticated"]:
            user = user_info.get("user", "unknown")
            logger.info(f"Authenticated user '{user}' accessing {func.__name__}")
        else:
            logger.info(f"Anonymous access to {func.__name__}")
        
        return await func(*args, **kwargs)
    
    return wrapper