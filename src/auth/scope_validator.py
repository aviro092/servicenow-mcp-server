"""Scope validation utilities for FastMCP ServiceNow server."""

import logging
from typing import Optional
from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import get_auth_config
import builtins

logger = logging.getLogger(__name__)


def get_authorization_header() -> Optional[str]:
    """Extract Authorization header from the current request context or environment."""
    try:
        # Method 1: Try to extract from request context (FastMCP HTTP)
        import inspect
        
        # Look for a request object in the call stack
        frame = inspect.currentframe()
        while frame:
            local_vars = frame.f_locals
            
            # Check for various request object patterns
            for var_name in ['request', 'req', 'http_request']:
                if var_name in local_vars:
                    request = local_vars[var_name]
                    if hasattr(request, 'headers'):
                        auth_header = request.headers.get('authorization') or request.headers.get('Authorization')
                        if auth_header:
                            logger.debug(f"[SCOPE] Found Authorization header in {var_name}")
                            return auth_header
                    elif hasattr(request, 'scope') and 'headers' in request.scope:
                        # ASGI-style headers
                        headers = dict(request.scope['headers'])
                        auth_header = headers.get(b'authorization') or headers.get(b'Authorization')
                        if auth_header:
                            logger.debug("[SCOPE] Found Authorization header in ASGI scope")
                            return auth_header.decode('utf-8')
            
            frame = frame.f_back
        
        # Method 2: Check for test token in environment (for testing)
        import os
        test_token = os.environ.get('MCP_TEST_AUTH_TOKEN')
        if test_token:
            logger.debug("[SCOPE] Using test token from environment variable")
            return f"Bearer {test_token}"
            
        logger.debug("[SCOPE] No Authorization header found")
        return None
        
    except Exception as e:
        logger.debug(f"[SCOPE] Could not extract Authorization header: {e}")
        return None


def require_scope(required_scope: str) -> None:
    """Check if the current authenticated user has the required scope.
    
    Args:
        required_scope: The scope required to access this resource
        
    Raises:
        Exception: If authentication fails or scope is missing
    """
    try:
        logger.debug(f"[SCOPE] Checking required scope: {required_scope}")
        
        # Check if authentication is enabled
        auth_config = get_auth_config()
        if not auth_config.enable_auth:
            logger.debug("[SCOPE] ✅ Authentication disabled, allowing request")
            return
        
        # Get the global auth provider
        auth_provider = getattr(builtins, 'global_auth_provider', None)
        if not auth_provider:
            logger.warning("[SCOPE] ⚠️  No auth provider available, allowing request")
            return
        
        # Try to extract Authorization header
        auth_header = get_authorization_header()
        if not auth_header:
            logger.warning("[SCOPE] ❌ No Authorization header provided")
            raise Exception("Authentication required: Missing Authorization header")
        
        # Validate Bearer token format
        if not auth_header.startswith("Bearer "):
            logger.warning("[SCOPE] ❌ Invalid Authorization header format")
            raise Exception("Authentication required: Invalid Authorization header format")
        
        # Extract token
        token = auth_header[7:]  # Remove "Bearer " prefix
        logger.debug(f"[SCOPE] Extracted token from Authorization header")
        
        # Verify token using auth provider
        import asyncio
        try:
            # Run the async authentication in the current context
            access_token = asyncio.create_task(auth_provider.authenticate(token))
            access_token = asyncio.get_event_loop().run_until_complete(access_token)
        except RuntimeError:
            # If no event loop is running, create a new one
            access_token = asyncio.run(auth_provider.authenticate(token))
        
        if not access_token:
            logger.warning("[SCOPE] ❌ Token verification failed")
            raise Exception("Authentication failed: Invalid or expired token")
        
        logger.info(f"[SCOPE] ✅ Token verified for user: {access_token.claims.get('sub', 'unknown')}")
        
        # Check if token has required scope
        if not access_token.has_scope(required_scope):
            logger.warning(f"[SCOPE] ❌ Access DENIED - Missing scope '{required_scope}'. Available: {access_token.scopes}")
            raise Exception(f"Access denied: Insufficient permissions. Required scope: {required_scope}")
        
        logger.info(f"[SCOPE] ✅ Access GRANTED - Scope '{required_scope}' verified for user: {access_token.claims.get('sub', 'unknown')}")
        
    except Exception as e:
        logger.error(f"[SCOPE] ❌ Authentication failed: {e}")
        # Re-raise the exception to actually enforce authentication
        raise


def get_current_user_info() -> Optional[dict]:
    """Get information about the currently authenticated user.
    
    Returns:
        Dictionary with user information if authenticated, None otherwise
    """
    try:
        token = get_access_token()
        if not token:
            return None
            
        return {
            "user_id": token.claims.get("sub"),
            "issuer": token.claims.get("iss"),
            "audience": token.claims.get("aud"),
            "scopes": token.scopes,
            "expires": token.claims.get("exp")
        }
    except Exception as e:
        logger.debug(f"Could not get user info: {e}")
        return None