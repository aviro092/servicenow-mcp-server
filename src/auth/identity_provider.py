"""Identity Provider authentication for FastMCP ServiceNow server."""

import logging
from typing import Optional, Any, Dict
import jwt
from jwt import PyJWKClient

from config import get_auth_config

logger = logging.getLogger(__name__)


class AccessToken:
    """Simple AccessToken implementation for our authentication."""
    
    def __init__(self, token: str, claims: dict, scopes: list):
        self.token = token
        self.claims = claims
        self.scopes = scopes
        
    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


class IdentityProviderAuth:
    """Identity provider authentication using JWKS for token verification."""
    
    def __init__(
        self,
        jwks_uri: Optional[str] = None,
        api_identifier: Optional[str] = None,
        mock_tokens: Optional[list[str]] = None,
        auth_mode: Optional[str] = None,
    ):
        """Initialize the Identity Provider authentication.
        
        Args:
            jwks_uri: JWKS URI for token verification (uses config if not provided)
            api_identifier: API identifier for audience validation (uses config if not provided)
            mock_tokens: List of valid mock tokens for testing (uses config if not provided)
            auth_mode: Authentication mode - 'identity-provider' or 'mock' (uses config if not provided)
        """
        super().__init__()
        
        # Load configuration
        self.config = get_auth_config()
        
        # Use provided values or fall back to config
        self.auth_mode = auth_mode or self.config.auth_mode
        self.jwks_uri = jwks_uri or self.config.identity_jwks_uri
        self.api_identifier = api_identifier or self.config.api_identifier
        self.mock_tokens = mock_tokens or self.config.mock_tokens
        
        self.jwks_client = None
        
        logger.info(f"Initializing Identity Provider Auth - mode: {self.auth_mode}")
        
        if self.auth_mode == "identity-provider":
            try:
                self.jwks_client = PyJWKClient(self.jwks_uri)
                logger.info(f"Initialized JWKS client with URI: {self.jwks_uri}")
            except Exception as e:
                logger.error(f"Failed to initialize JWKS client: {e}")
                raise
        elif self.auth_mode == "mock":
            logger.info(f"Mock authentication enabled with {len(self.mock_tokens)} valid tokens")
        elif self.auth_mode == "oauth":
            logger.info("OAuth authentication mode enabled - tokens will be validated using demo JWT signing")
        else:
            logger.warning(f"Unknown auth mode: {self.auth_mode}, authentication may not work properly")
    
    async def authenticate(self, token: str) -> Optional[AccessToken]:
        """Authenticate and return AccessToken if valid."""
        # Log token receipt with partial preview
        token_preview = f"{token[:20]}...{token[-10:]}" if len(token) > 30 else token[:50]
        logger.info(f"[AUTH] Received token for authentication: {token_preview}")
        
        try:
            if self.auth_mode == "mock":
                logger.debug(f"[AUTH] Using mock authentication mode")
                return await self._verify_mock_token(token)
            elif self.auth_mode == "identity-provider":
                logger.debug(f"[AUTH] Using identity-provider authentication mode")
                return await self._verify_identity_provider_token(token)
            elif self.auth_mode == "oauth":
                logger.debug(f"[AUTH] Using OAuth authentication mode")
                return await self._verify_oauth_token(token)
            else:
                logger.error(f"[AUTH] Unknown auth mode: {self.auth_mode}")
                return None
                
        except Exception as e:
            logger.error(f"[AUTH] Token authentication failed: {e}")
            return None
    
    async def _verify_mock_token(self, token: str) -> Optional[AccessToken]:
        """Verify mock token for testing purposes."""
        logger.info(f"[AUTH] Verifying mock token against {len(self.mock_tokens)} valid tokens")
        
        if token in self.mock_tokens:
            logger.info("[AUTH] Mock token verification PASSED - token is valid")
            
            # Create mock claims with all scopes for testing
            mock_claims = {
                "sub": "mock-user",
                "iss": "mock-issuer",
                "aud": self.api_identifier,
                "scope": " ".join(self.config.all_scopes),
                "exp": 9999999999  # Far future expiry
            }
            
            logger.info(f"[AUTH] Mock user authenticated - user: mock-user, scopes: {self.config.all_scopes}")
            
            return AccessToken(
                token=token,
                claims=mock_claims,
                scopes=self.config.all_scopes
            )
        
        logger.warning(f"[AUTH] Mock token verification FAILED - invalid token")
        return None
    
    async def _verify_identity_provider_token(self, token: str) -> Optional[AccessToken]:
        """Verify JWT token using identity provider JWKS."""
        if not self.jwks_client:
            logger.error("[AUTH] JWKS client not initialized")
            return None
        
        try:
            logger.info(f"[AUTH] Starting JWT token verification using JWKS endpoint: {self.jwks_uri}")
            
            # Get signing key from JWKS
            logger.debug("[AUTH] Fetching signing key from JWKS endpoint...")
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            logger.debug("[AUTH] Successfully retrieved signing key from JWKS")
            
            # Check if this is a flexible identity provider that may use different audience format
            is_flexible_provider = any(provider in self.jwks_uri.lower() for provider in ['identity', 'auth0', 'okta', 'keycloak'])
            
            if is_flexible_provider:
                logger.debug("[AUTH] Detected flexible identity provider - using relaxed validation")
                # Some identity providers may have different audience format
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    options={
                        "verify_exp": True,
                        "verify_aud": False  # Identity provider may not include our API identifier in audience
                    }
                )
            else:
                # Standard OIDC validation
                logger.debug(f"[AUTH] Decoding JWT token with audience: {self.api_identifier}")
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=self.api_identifier,
                    options={"verify_exp": True}
                )
            
            logger.info("[AUTH] JWT token verification PASSED - token is valid")
            logger.info(f"[AUTH] User authenticated - sub: {claims.get('sub')}, iss: {claims.get('iss')}")
            
            # Extract scopes from token - identity providers may use different claim names
            scopes = []
            
            # Try different scope claim formats
            for scope_claim in ["scope", "scp", "scopes"]:
                if scope_claim in claims:
                    scope_value = claims[scope_claim]
                    if isinstance(scope_value, str):
                        scopes = scope_value.split()
                    elif isinstance(scope_value, list):
                        scopes = scope_value
                    break
            
            # For flexible identity providers, if no scopes found, grant default scopes based on client
            if not scopes and is_flexible_provider:
                # Check if this is a valid identity provider token by looking for standard claims
                identity_claims = [
                    "sub",
                    "iss",
                    "client_id",
                    "azp"  # Authorized party claim
                ]
                
                if any(claim in claims for claim in identity_claims):
                    # Grant default scopes for authenticated identity provider users
                    scopes = self.config.all_scopes
                    logger.info("[AUTH] Identity provider token detected - granted default scopes")
            
            if scopes:
                logger.info(f"[AUTH] Token scopes extracted: {scopes}")
            else:
                logger.warning("[AUTH] No scopes found in token")
            
            return AccessToken(
                token=token,
                claims=claims,
                scopes=scopes
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("[AUTH] JWT verification FAILED - token has expired")
            return None
        except jwt.InvalidAudienceError:
            logger.warning(f"[AUTH] JWT verification FAILED - invalid audience (expected: {self.api_identifier})")
            return None
        except jwt.InvalidSignatureError:
            logger.warning("[AUTH] JWT verification FAILED - invalid signature")
            return None
        except Exception as e:
            logger.error(f"[AUTH] JWT verification FAILED - error: {e}")
            return None
    
    async def _verify_oauth_token(self, token: str) -> Optional[AccessToken]:
        """Verify OAuth JWT token issued by our OAuth server."""
        try:
            logger.info(f"[AUTH] Starting OAuth JWT token verification")
            
            # Verify and decode token using our demo secret (in production, use proper key management)
            logger.debug("[AUTH] Decoding OAuth JWT token...")
            claims = jwt.decode(
                token,
                "demo-secret",  # In production, use proper signing key
                algorithms=["HS256"],
                options={"verify_exp": True, "verify_aud": False}  # More permissive for demo
            )
            
            logger.info("[AUTH] OAuth JWT token verification PASSED - token is valid")
            logger.info(f"[AUTH] OAuth user authenticated - sub: {claims.get('sub')}, client_id: {claims.get('client_id')}")
            
            # Extract scopes from token
            scopes = []
            if "scope" in claims:
                scopes = claims["scope"].split() if isinstance(claims["scope"], str) else []
                logger.info(f"[AUTH] OAuth token scopes extracted: {scopes}")
            else:
                logger.warning("[AUTH] No scopes found in OAuth token")
            
            return AccessToken(
                token=token,
                claims=claims,
                scopes=scopes
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("[AUTH] OAuth JWT verification FAILED - token has expired")
            return None
        except jwt.InvalidSignatureError:
            logger.warning("[AUTH] OAuth JWT verification FAILED - invalid signature")
            return None
        except Exception as e:
            logger.error(f"[AUTH] OAuth JWT verification FAILED - error: {e}")
            return None


# Create instance with environment variable configuration
def create_identity_provider() -> IdentityProviderAuth:
    """Create IdentityProviderAuth instance from environment configuration."""
    return IdentityProviderAuth()