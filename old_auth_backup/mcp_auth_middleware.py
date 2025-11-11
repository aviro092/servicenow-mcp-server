"""MCP authentication middleware to capture Bearer tokens from HTTP requests."""

import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import contextvars
from auth.oauth_provider import OAuthProvider
from config import get_auth_config

logger = logging.getLogger(__name__)

# Context variable to store the current request's Bearer token
current_bearer_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'current_bearer_token', default=None
)


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to capture Bearer tokens from HTTP requests and handle OAuth authentication."""
    
    def __init__(self, app):
        super().__init__(app)
        self.oauth_provider = OAuthProvider()
        self.auth_config = get_auth_config()
    
    async def dispatch(self, request: Request, call_next):
        """Extract Bearer token from Authorization header and handle OAuth flow."""
        
        # Skip authentication for OAuth endpoints
        oauth_paths = [
            "/.well-known/oauth-protected-resource",
            "/.well-known/oauth-authorization-server", 
            "/oauth/authorize",
            "/oauth/token",
            "/oauth/register",
            "/oauth/userinfo",
            "/health"
        ]
        
        # Check if this is an OAuth endpoint or health check
        if any(request.url.path.startswith(path) for path in oauth_paths):
            return await call_next(request)
        
        # Extract Authorization header
        auth_header = request.headers.get('authorization') or request.headers.get('Authorization')
        token = None
        
        if auth_header:
            logger.debug(f"[MIDDLEWARE] Found Authorization header: {auth_header[:50]}...")
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove "Bearer " prefix
                logger.info("[MIDDLEWARE] Extracted Bearer token from Authorization header")
                token_preview = f"{token[:20]}...{token[-10:]}" if len(token) > 30 else token[:50]
                logger.debug(f"[MIDDLEWARE] Token preview: {token_preview}")
            else:
                logger.warning("[MIDDLEWARE] Authorization header does not start with 'Bearer '")
        else:
            logger.debug("[MIDDLEWARE] No Authorization header found in request")
        
        # Store token in context variable for handlers to access
        current_bearer_token.set(token)
        
        # If authentication is enabled and mode is OAuth, check for missing token
        if (self.auth_config.enable_auth and 
            self.auth_config.auth_mode == "oauth" and 
            not token and
            request.url.path.startswith('/mcp/')):  # Only enforce on MCP endpoints
            
            logger.warning("[MIDDLEWARE] Missing Bearer token for OAuth authentication")
            
            # Return 401 with WWW-Authenticate header per MCP OAuth spec
            www_auth_header = self.oauth_provider.generate_www_authenticate_header(
                error="invalid_token",
                error_description="Bearer token required"
            )
            
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "error_description": "Bearer token required"},
                headers={"WWW-Authenticate": www_auth_header}
            )
        
        # Process the request
        response = await call_next(request)
        
        # Clear the token from context after request
        current_bearer_token.set(None)
        
        return response


def get_current_bearer_token() -> Optional[str]:
    """Get the current Bearer token from the context variable."""
    token = current_bearer_token.get()
    if token:
        logger.debug(f"[MIDDLEWARE] Retrieved token from context: {token[:20]}...{token[-10:] if len(token) > 30 else ''}")
    else:
        logger.debug("[MIDDLEWARE] No token found in context")
    return token