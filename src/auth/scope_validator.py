"""Scope validation utilities for FastMCP ServiceNow server."""

import logging
from typing import Optional
from fastmcp.server.dependencies import get_access_token
from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)


def require_scope(required_scope: str) -> None:
    """Check if the current authenticated user has the required scope.
    
    This function should be called at the beginning of tool handlers that require
    specific scopes. It will raise a ToolError if the user doesn't have the required scope.
    
    Args:
        required_scope: The scope required to access this resource
        
    Raises:
        ToolError: If authentication is required but user doesn't have the scope
    """
    try:
        logger.debug(f"[SCOPE] Checking required scope: {required_scope}")
        
        # Get the current access token from FastMCP context
        token = get_access_token()
        
        if not token:
            logger.warning(f"[SCOPE] ❌ No access token available for scope check: {required_scope}")
            raise ToolError("Authentication required: No valid access token")
        
        logger.debug(f"[SCOPE] Found access token for user: {token.claims.get('sub', 'unknown')}")
        logger.debug(f"[SCOPE] Available scopes in token: {token.scopes}")
        
        # Check if the token has the required scope
        if not token.has_scope(required_scope):
            logger.warning(f"[SCOPE] ❌ Access DENIED - Token missing required scope '{required_scope}'. Available scopes: {token.scopes}")
            raise ToolError(f"Access denied: Insufficient permissions. Required scope: {required_scope}")
        
        logger.info(f"[SCOPE] ✅ Access GRANTED - Scope check passed for '{required_scope}' - user: {token.claims.get('sub', 'unknown')}")
        
    except ToolError:
        # Re-raise ToolError as-is
        raise
    except Exception as e:
        logger.error(f"[SCOPE] ❌ Scope validation error: {e}")
        raise ToolError(f"Authentication error: {str(e)}")


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