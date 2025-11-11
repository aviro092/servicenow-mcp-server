"""Simplified unified authentication for ServiceNow MCP Server."""

import logging
import os
from typing import Optional, Dict, Any
import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


class UnifiedAuth:
    """Simplified authentication handler for all auth modes."""
    
    def __init__(self, config):
        """Initialize authentication with config."""
        self.config = config
        self.enabled = config.enable_auth
        self.mode = config.auth_mode if self.enabled else "disabled"
        
        # Initialize JWKS client if needed
        self.jwks_client = None
        if self.mode == "identity-provider" and config.identity_jwks_uri:
            try:
                self.jwks_client = PyJWKClient(config.identity_jwks_uri)
                logger.info(f"Initialized JWKS client: {config.identity_jwks_uri}")
            except Exception as e:
                logger.error(f"Failed to initialize JWKS: {e}")
                self.mode = "disabled"  # Fallback to disabled on error
    
    async def validate_token(self, token: Optional[str]) -> Dict[str, Any]:
        """Validate token and return user info with scopes.
        
        Returns dict with:
        - authenticated: bool
        - user: str (user identifier)
        - scopes: list of scope strings
        - error: str (if authentication failed)
        """
        # No auth required
        if not self.enabled:
            return {
                "authenticated": True,
                "user": "anonymous",
                "scopes": self.config.all_scopes,
                "mode": "disabled"
            }
        
        # Token required but missing
        if not token:
            return {
                "authenticated": False,
                "error": "Bearer token required",
                "mode": self.mode
            }
        
        # Validate based on mode
        try:
            if self.mode == "mock":
                return self._validate_mock(token)
            elif self.mode == "identity-provider":
                return await self._validate_jwt(token)
            elif self.mode == "oauth":
                return self._validate_oauth(token)
            else:
                return {
                    "authenticated": False,
                    "error": f"Unknown auth mode: {self.mode}",
                    "mode": self.mode
                }
        except Exception as e:
            logger.error(f"Auth validation error: {e}")
            return {
                "authenticated": False,
                "error": str(e),
                "mode": self.mode
            }
    
    def _validate_mock(self, token: str) -> Dict[str, Any]:
        """Validate mock token for testing."""
        if token in self.config.mock_tokens:
            return {
                "authenticated": True,
                "user": "mock-user",
                "scopes": self.config.all_scopes,
                "mode": "mock"
            }
        return {
            "authenticated": False,
            "error": "Invalid mock token",
            "mode": "mock"
        }
    
    async def _validate_jwt(self, token: str) -> Dict[str, Any]:
        """Validate JWT token using JWKS."""
        if not self.jwks_client:
            return {
                "authenticated": False,
                "error": "JWKS client not initialized",
                "mode": "identity-provider"
            }
        
        try:
            # Get signing key and decode token
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_exp": True, "verify_aud": False}
            )
            
            # Extract scopes
            scopes = []
            for claim in ["scope", "scp", "scopes"]:
                if claim in claims:
                    scope_value = claims[claim]
                    scopes = scope_value.split() if isinstance(scope_value, str) else scope_value
                    break
            
            # Default scopes if none found
            if not scopes and claims.get("sub"):
                scopes = self.config.all_scopes
            
            return {
                "authenticated": True,
                "user": claims.get("sub", "unknown"),
                "scopes": scopes,
                "claims": claims,
                "mode": "identity-provider"
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "authenticated": False,
                "error": "Token expired",
                "mode": "identity-provider"
            }
        except Exception as e:
            return {
                "authenticated": False,
                "error": f"JWT validation failed: {str(e)}",
                "mode": "identity-provider"
            }
    
    def _validate_oauth(self, token: str) -> Dict[str, Any]:
        """Validate OAuth token (simplified demo version)."""
        try:
            # For demo, use simple HS256 validation
            claims = jwt.decode(
                token,
                "demo-secret",  # In production, use proper key management
                algorithms=["HS256"],
                options={"verify_exp": True, "verify_aud": False}
            )
            
            scopes = claims.get("scope", "").split() if "scope" in claims else []
            
            return {
                "authenticated": True,
                "user": claims.get("sub", claims.get("client_id", "unknown")),
                "scopes": scopes or self.config.all_scopes,
                "claims": claims,
                "mode": "oauth"
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "authenticated": False,
                "error": "Token expired",
                "mode": "oauth"
            }
        except Exception as e:
            return {
                "authenticated": False,
                "error": f"OAuth validation failed: {str(e)}",
                "mode": "oauth"
            }
    
    def check_scope(self, user_scopes: list, required_scope: str) -> bool:
        """Check if user has required scope."""
        if not self.enabled:
            return True  # No auth = all scopes allowed
        return required_scope in user_scopes
    
    def generate_www_authenticate(self, error: str = None) -> str:
        """Generate WWW-Authenticate header for 401 responses."""
        parts = [
            f'realm="{self.config.realm}"',
            f'resource="{self.config.resource_server_url}"',
            f'resource_metadata="{self.config.resource_server_url}/.well-known/oauth-protected-resource"'
        ]
        
        if error:
            parts.append(f'error="{error}"')
            
        return f"Bearer {', '.join(parts)}"


# Singleton instance
_auth_instance: Optional[UnifiedAuth] = None


def get_auth() -> UnifiedAuth:
    """Get the singleton auth instance."""
    global _auth_instance
    if _auth_instance is None:
        from config import get_auth_config
        _auth_instance = UnifiedAuth(get_auth_config())
    return _auth_instance


async def authenticate_request(token: Optional[str] = None) -> Dict[str, Any]:
    """Simple function to authenticate a request.
    
    Args:
        token: Bearer token from Authorization header
        
    Returns:
        Dict with authentication result
    """
    auth = get_auth()
    
    # Try to get token from environment if not provided (for testing)
    if not token and auth.enabled:
        token = os.environ.get('MCP_TEST_AUTH_TOKEN')
    
    return await auth.validate_token(token)


async def require_scope(token: Optional[str], required_scope: str) -> Dict[str, Any]:
    """Authenticate and check for required scope.
    
    Args:
        token: Bearer token
        required_scope: Required scope string
        
    Returns:
        Dict with authentication result and scope check
        
    Raises:
        HTTPException: If authentication fails or scope missing
    """
    from fastapi import HTTPException
    
    # Authenticate
    result = await authenticate_request(token)
    
    if not result["authenticated"]:
        raise HTTPException(
            status_code=401,
            detail=result.get("error", "Authentication failed"),
            headers={"WWW-Authenticate": get_auth().generate_www_authenticate("invalid_token")}
        )
    
    # Check scope
    auth = get_auth()
    if not auth.check_scope(result.get("scopes", []), required_scope):
        raise HTTPException(
            status_code=403,
            detail=f"Missing required scope: {required_scope}"
        )
    
    return result