"""Scope validation utilities for FastMCP ServiceNow server."""

import logging
from typing import Optional
from config import get_auth_config

logger = logging.getLogger(__name__)


def require_scope(required_scope: str) -> None:
    """Check if the current authenticated user has the required scope.
    
    For now, this is a placeholder implementation. In a future version,
    this will integrate with FastMCP's authentication system.
    
    Args:
        required_scope: The scope required to access this resource
    """
    try:
        logger.debug(f"[SCOPE] Checking required scope: {required_scope}")
        
        # Check if authentication is enabled
        auth_config = get_auth_config()
        if not auth_config.enable_auth:
            logger.debug("[SCOPE] ✅ Authentication disabled, allowing request")
            return
        
        # For now, we'll log the requirement but not enforce it
        # This will be updated when FastMCP integration is completed
        logger.info(f"[SCOPE] ⚠️  Authentication enabled but not yet enforced - required scope: {required_scope}")
        logger.info(f"[SCOPE] ✅ Access GRANTED (temporary) - scope check for '{required_scope}'")
        
    except Exception as e:
        logger.error(f"[SCOPE] ❌ Scope validation error: {e}")
        # Don't raise errors for now to keep the system working
        logger.warning("[SCOPE] ⚠️  Continuing despite scope validation error")


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