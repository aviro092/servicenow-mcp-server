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
    logger.info(f"[SCOPE] 🔐 Authentication check started - Required scope: {required_scope}")
    
    # Check if authentication is enabled
    auth_config = get_auth_config()
    if not auth_config.enable_auth:
        logger.info("[AUTH] ✅ Authentication disabled, creating mock user")
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
    
    logger.info(f"[AUTH] 🔍 Starting token extraction process...")
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
            frame_count = 0
            max_frames = 20  # Limit search depth
            
            logger.debug("[AUTH] 🔍 Searching call stack for request context...")
            
            while frame and frame_count < max_frames:
                local_vars = frame.f_locals
                frame_info = f"Frame {frame_count}: {frame.f_code.co_filename}:{frame.f_code.co_name}"
                logger.debug(f"[AUTH] Checking {frame_info}")
                
                # Check for various request object patterns
                for var_name in ['request', 'req', 'http_request', 'scope', 'receive', 'send']:
                    if var_name in local_vars:
                        request_obj = local_vars[var_name]
                        logger.debug(f"[AUTH] Found {var_name}: {type(request_obj)}")
                        
                        # Method 2a: Standard request object with headers
                        if hasattr(request_obj, 'headers'):
                            logger.debug(f"[AUTH] Checking headers in {var_name}")
                            headers = request_obj.headers
                            logger.debug(f"[AUTH] Headers type: {type(headers)}, keys: {list(headers.keys()) if hasattr(headers, 'keys') else 'no keys method'}")
                            
                            # Try different header access methods
                            auth_header = None
                            for auth_key in ['authorization', 'Authorization', 'AUTHORIZATION']:
                                if hasattr(headers, 'get'):
                                    auth_header = headers.get(auth_key)
                                elif hasattr(headers, '__getitem__'):
                                    try:
                                        auth_header = headers[auth_key]
                                    except (KeyError, TypeError):
                                        continue
                                if auth_header:
                                    logger.debug(f"[AUTH] Found auth header with key '{auth_key}': {auth_header[:50]}...")
                                    break
                            
                            if auth_header and str(auth_header).startswith('Bearer '):
                                token = str(auth_header)[7:]  # Remove "Bearer " prefix
                                logger.info("[AUTH] 🔑 Extracted Bearer token from request headers")
                                break
                        
                        # Method 2b: ASGI scope with headers
                        elif hasattr(request_obj, 'scope') and isinstance(request_obj.scope, dict) and 'headers' in request_obj.scope:
                            logger.debug(f"[AUTH] Checking ASGI scope headers in {var_name}")
                            headers = dict(request_obj.scope['headers'])
                            logger.debug(f"[AUTH] ASGI headers: {list(headers.keys())}")
                            
                            auth_header = headers.get(b'authorization') or headers.get(b'Authorization')
                            if auth_header:
                                auth_str = auth_header.decode('utf-8')
                                logger.debug(f"[AUTH] Found ASGI auth header: {auth_str[:50]}...")
                                if auth_str.startswith('Bearer '):
                                    token = auth_str[7:]
                                    logger.info("[AUTH] 🔑 Extracted Bearer token from ASGI scope")
                                    break
                        
                        # Method 2c: Direct scope dict
                        elif isinstance(request_obj, dict) and 'headers' in request_obj:
                            logger.debug(f"[AUTH] Checking direct scope dict headers in {var_name}")
                            headers = dict(request_obj['headers'])
                            logger.debug(f"[AUTH] Scope dict headers: {list(headers.keys())}")
                            
                            auth_header = headers.get(b'authorization') or headers.get(b'Authorization')
                            if auth_header:
                                auth_str = auth_header.decode('utf-8')
                                logger.debug(f"[AUTH] Found scope dict auth header: {auth_str[:50]}...")
                                if auth_str.startswith('Bearer '):
                                    token = auth_str[7:]
                                    logger.info("[AUTH] 🔑 Extracted Bearer token from scope dict")
                                    break
                
                if token:
                    break
                frame = frame.f_back
                frame_count += 1
                
            if frame_count >= max_frames:
                logger.debug(f"[AUTH] Reached maximum frame search depth ({max_frames})")
                
        except Exception as e:
            logger.error(f"[AUTH] Error extracting token from request context: {e}")
            import traceback
            logger.debug(f"[AUTH] Traceback: {traceback.format_exc()}")
    
    # Method 3: Try to get from FastMCP context globals
    if not token:
        try:
            # Check if FastMCP stores request context in globals
            for global_var in ['_current_request', '_mcp_request', '_fastmcp_request']:
                if hasattr(builtins, global_var):
                    request_obj = getattr(builtins, global_var)
                    logger.debug(f"[AUTH] Found global request context: {global_var}")
                    if hasattr(request_obj, 'headers'):
                        auth_header = request_obj.headers.get('authorization') or request_obj.headers.get('Authorization')
                        if auth_header and auth_header.startswith('Bearer '):
                            token = auth_header[7:]
                            logger.info("[AUTH] 🔑 Extracted Bearer token from global context")
                            break
        except Exception as e:
            logger.debug(f"[AUTH] Could not extract from global context: {e}")
    
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