"""Scope validation utilities for FastMCP ServiceNow server."""

import logging
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import get_auth_config
from .identity_provider import AccessToken
import builtins
import os

logger = logging.getLogger(__name__)

# HTTPBearer security scheme for standard Bearer token authentication
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AccessToken:
    """Get current authenticated user from Bearer token using FastAPI dependency injection."""
    
    # Check if authentication is enabled
    auth_config = get_auth_config()
    if not auth_config.enable_auth:
        logger.debug("[AUTH] ✅ Authentication disabled, creating mock user")
        # Return mock user when auth is disabled
        return AccessToken(
            token="disabled",
            claims={"sub": "mock-user-auth-disabled"},
            scopes=auth_config.all_scopes
        )
    
    # Get the global auth provider
    auth_provider = getattr(builtins, 'global_auth_provider', None)
    if not auth_provider:
        logger.warning("[AUTH] ⚠️  No auth provider available")
        raise HTTPException(status_code=500, detail="Authentication provider not initialized")
    
    # Try to get token from Authorization header first
    token = None
    if credentials:
        token = credentials.credentials
        logger.info(f"[AUTH] 🔑 Extracted Bearer token from Authorization header")
        token_preview = f"{token[:20]}...{token[-10:]}" if len(token) > 30 else token
        logger.debug(f"[AUTH] Token preview: {token_preview}")
    
    # Fallback to test token from environment (for testing)
    if not token:
        test_token = os.environ.get('MCP_TEST_AUTH_TOKEN')
        if test_token:
            token = test_token
            logger.debug("[AUTH] 🧪 Using test token from MCP_TEST_AUTH_TOKEN environment variable")
    
    if not token:
        logger.warning("[AUTH] ❌ No Bearer token provided")
        raise HTTPException(status_code=401, detail="Bearer token required")
    
    # Verify token using auth provider
    try:
        # Run the async authentication directly since we're now async
        access_token = await auth_provider.authenticate(token)
        
        if not access_token:
            logger.warning("[AUTH] ❌ Bearer token validation failed")
            raise HTTPException(status_code=401, detail="Invalid Bearer token")
        
        logger.info(f"[AUTH] ✅ Bearer authentication successful for user: {access_token.claims.get('sub', 'unknown')}")
        return access_token
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"[AUTH] ❌ Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def require_scope(required_scope: str):
    """FastAPI dependency to check if user has required scope."""
    async def scope_checker(user: AccessToken = Depends(get_current_user)) -> AccessToken:
        logger.debug(f"[SCOPE] Checking required scope: {required_scope}")
        logger.debug(f"[SCOPE] User: {user.claims.get('sub', 'unknown')}, Available scopes: {user.scopes}")
        
        if required_scope not in user.scopes:
            logger.warning(f"[SCOPE] ❌ Access DENIED - Missing scope '{required_scope}'. Available: {user.scopes}")
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        
        logger.info(f"[SCOPE] ✅ Access GRANTED - Scope '{required_scope}' verified for user: {user.claims.get('sub', 'unknown')}")
        return user
    
    return scope_checker


async def check_scope_access(required_scope: str) -> AccessToken:
    """Check authentication and scope access for FastMCP handlers.
    
    This function is designed to work with FastMCP which doesn't support 
    FastAPI dependency injection, so we handle authentication manually.
    
    Args:
        required_scope: The scope required to access this resource
        
    Returns:
        AccessToken: The authenticated user's token
        
    Raises:
        HTTPException: If authentication or authorization fails
    """
    logger.debug(f"[SCOPE] Checking required scope: {required_scope}")
    
    # Check if authentication is enabled
    auth_config = get_auth_config()
    if not auth_config.enable_auth:
        logger.debug("[AUTH] ✅ Authentication disabled, creating mock user")
        # Return mock user when auth is disabled
        return AccessToken(
            token="disabled",
            claims={"sub": "mock-user-auth-disabled"},
            scopes=auth_config.all_scopes
        )
    
    # Get the global auth provider
    auth_provider = getattr(builtins, 'global_auth_provider', None)
    if not auth_provider:
        logger.warning("[AUTH] ⚠️  No auth provider available")
        raise HTTPException(status_code=500, detail="Authentication provider not initialized")
    
    # Try to get token from various sources since we can't use FastAPI dependency injection
    token = None
    
    # Method 1: Check environment variable (for testing)
    test_token = os.environ.get('MCP_TEST_AUTH_TOKEN')
    if test_token:
        token = test_token
        logger.debug("[AUTH] 🧪 Using test token from MCP_TEST_AUTH_TOKEN environment variable")
    
    # Method 2: Try to extract from request context if available
    if not token:
        try:
            import inspect
            frame = inspect.currentframe()
            while frame:
                local_vars = frame.f_locals
                for var_name in ['request', 'req', 'http_request']:
                    if var_name in local_vars:
                        request = local_vars[var_name]
                        if hasattr(request, 'headers'):
                            auth_header = request.headers.get('authorization') or request.headers.get('Authorization')
                            if auth_header and auth_header.startswith('Bearer '):
                                token = auth_header[7:]  # Remove "Bearer " prefix
                                logger.info("[AUTH] 🔑 Extracted Bearer token from request headers")
                                break
                        elif hasattr(request, 'scope') and 'headers' in request.scope:
                            headers = dict(request.scope['headers'])
                            auth_header = headers.get(b'authorization') or headers.get(b'Authorization')
                            if auth_header and auth_header.decode('utf-8').startswith('Bearer '):
                                token = auth_header.decode('utf-8')[7:]
                                logger.info("[AUTH] 🔑 Extracted Bearer token from ASGI scope")
                                break
                if token:
                    break
                frame = frame.f_back
        except Exception as e:
            logger.debug(f"[AUTH] Could not extract token from request context: {e}")
    
    if not token:
        logger.warning("[AUTH] ❌ No Bearer token provided")
        raise HTTPException(status_code=401, detail="Bearer token required")
    
    # Verify token using auth provider
    try:
        access_token = await auth_provider.authenticate(token)
        
        if not access_token:
            logger.warning("[AUTH] ❌ Bearer token validation failed")
            raise HTTPException(status_code=401, detail="Invalid Bearer token")
        
        logger.info(f"[AUTH] ✅ Bearer authentication successful for user: {access_token.claims.get('sub', 'unknown')}")
        
        # Check if token has required scope
        if required_scope not in access_token.scopes:
            logger.warning(f"[SCOPE] ❌ Access DENIED - Missing scope '{required_scope}'. Available: {access_token.scopes}")
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        
        logger.info(f"[SCOPE] ✅ Access GRANTED - Scope '{required_scope}' verified for user: {access_token.claims.get('sub', 'unknown')}")
        return access_token
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"[AUTH] ❌ Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


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