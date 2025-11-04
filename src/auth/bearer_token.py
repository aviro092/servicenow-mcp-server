"""Token verification module for ServiceNow MCP Server."""

import logging
from typing import Optional, Dict, Any, List
import jwt
from jwt import PyJWKClient
from functools import wraps
from config import get_auth_config

logger = logging.getLogger(__name__)


class AccessToken:
    """Represents a validated access token with claims and scopes."""
    
    def __init__(self, token: str, claims: Dict[str, Any]):
        self.token = token
        self.claims = claims
        self.sub = claims.get("sub")
        self.scopes = claims.get("scope", "").split() if claims.get("scope") else []
        self.expires = claims.get("exp")
        self.issuer = claims.get("iss")
        self.audience = claims.get("aud")
    
    def has_scope(self, required_scope: str) -> bool:
        """Check if token has the required scope."""
        return required_scope in self.scopes
    
    def has_any_scope(self, required_scopes: List[str]) -> bool:
        """Check if token has any of the required scopes."""
        return any(scope in self.scopes for scope in required_scopes)


class IdentityAuthProvider:
    """Identity provider authentication using JWKS for token verification."""
    
    def __init__(self):
        self.config = get_auth_config()
        self.jwks_client = None
        
        if self.config.auth_mode == "identity-provider":
            try:
                self.jwks_client = PyJWKClient(self.config.identity_jwks_uri)
                logger.info(f"Initialized JWKS client with URI: {self.config.identity_jwks_uri}")
            except Exception as e:
                logger.error(f"Failed to initialize JWKS client: {e}")
                raise
    
    def verify_token(self, token: str) -> Optional[AccessToken]:
        """Verify JWT token and return AccessToken if valid."""
        try:
            if self.config.auth_mode == "mock":
                return self._verify_mock_token(token)
            elif self.config.auth_mode == "identity-provider":
                return self._verify_identity_provider_token(token)
            else:
                logger.error(f"Unknown auth mode: {self.config.auth_mode}")
                return None
                
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    def _verify_mock_token(self, token: str) -> Optional[AccessToken]:
        """Verify mock token for testing purposes."""
        if token in self.config.mock_tokens:
            logger.debug("Mock token verified successfully")
            
            # Create mock claims with all scopes for testing
            mock_claims = {
                "sub": "mock-user",
                "iss": "mock-issuer",
                "aud": self.config.api_identifier,
                "scope": " ".join(self.config.all_scopes),
                "exp": 9999999999  # Far future expiry
            }
            
            return AccessToken(token, mock_claims)
        
        logger.warning(f"Invalid mock token: {token}")
        return None
    
    def _verify_identity_provider_token(self, token: str) -> Optional[AccessToken]:
        """Verify JWT token using identity provider JWKS."""
        if not self.jwks_client:
            logger.error("JWKS client not initialized")
            return None
        
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Verify and decode token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.config.api_identifier,
                options={"verify_exp": True}
            )
            
            logger.debug("Identity provider token verified successfully")
            return AccessToken(token, claims)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience")
            return None
        except jwt.InvalidSignatureError:
            logger.warning("Invalid token signature")
            return None
        except Exception as e:
            logger.error(f"Identity provider token verification failed: {e}")
            return None


# Global auth provider instance
_auth_provider: Optional[IdentityAuthProvider] = None


def get_auth_provider() -> IdentityAuthProvider:
    """Get or create the global auth provider instance."""
    global _auth_provider
    if _auth_provider is None:
        _auth_provider = IdentityAuthProvider()
    return _auth_provider


def get_current_user(auth_header: Optional[str]) -> Optional[AccessToken]:
    """Extract and verify bearer token from Authorization header."""
    if not auth_header:
        return None
    
    # Check for Bearer token format
    if not auth_header.startswith("Bearer "):
        logger.warning("Invalid authorization header format")
        return None
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    auth_provider = get_auth_provider()
    return auth_provider.verify_token(token)


def require_scope(required_scope: str):
    """Decorator to require specific scope for a function."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if authentication is enabled
            config = get_auth_config()
            if not config.enable_auth:
                logger.debug("Authentication disabled, skipping scope check")
                return await func(*args, **kwargs)
            
            # Extract token from request context
            # This will be implemented when integrating with FastMCP
            # For now, we'll skip the check
            logger.debug(f"Scope check for '{required_scope}' - implementation pending")
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator