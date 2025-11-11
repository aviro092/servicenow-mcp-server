"""Simplified authentication middleware."""

import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import contextvars

from .unified_auth import get_auth

logger = logging.getLogger(__name__)

# Context variable for current user
current_user: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar(
    'current_user', default=None
)


class SimpleAuthMiddleware(BaseHTTPMiddleware):
    """Simplified authentication middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Extract token and authenticate user."""
        
        # Skip auth for public endpoints
        public_paths = [
            "/.well-known/",
            "/oauth/",
            "/health"
        ]
        
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Extract Bearer token
        token = None
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        # Authenticate
        auth = get_auth()
        user_info = await auth.validate_token(token)
        
        # Store user in context
        current_user.set(user_info)
        
        # Check if authentication failed for protected endpoints
        if request.url.path.startswith('/mcp/') and not user_info["authenticated"]:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "detail": user_info.get("error", "Authentication required")},
                headers={"WWW-Authenticate": auth.generate_www_authenticate("invalid_token")}
            )
        
        return await call_next(request)


def get_current_user() -> Optional[dict]:
    """Get current authenticated user info."""
    return current_user.get()


def require_scope_simple(required_scope: str) -> dict:
    """Check if current user has required scope."""
    from fastapi import HTTPException
    
    user_info = get_current_user()
    
    if not user_info:
        raise HTTPException(status_code=401, detail="No authentication context")
    
    if not user_info["authenticated"]:
        raise HTTPException(
            status_code=401,
            detail=user_info.get("error", "Authentication required")
        )
    
    auth = get_auth()
    if not auth.check_scope(user_info.get("scopes", []), required_scope):
        raise HTTPException(
            status_code=403,
            detail=f"Missing required scope: {required_scope}"
        )
    
    return user_info