"""OAuth authentication provider for MCP server."""

import json
import logging
import secrets
import urllib.parse
from typing import Dict, Optional, Any
from fastapi import HTTPException
import httpx
from config import get_auth_config

logger = logging.getLogger(__name__)


class OAuthProvider:
    """OAuth authentication provider for MCP server."""
    
    def __init__(self):
        """Initialize OAuth provider."""
        self.config = get_auth_config()
        self._client_registrations: Dict[str, Dict[str, Any]] = {}
        
    def get_protected_resource_metadata(self) -> Dict[str, Any]:
        """Generate Protected Resource Metadata (PRM) document.
        
        Returns:
            Dictionary containing resource metadata per RFC 8707
        """
        # Extract authorization server base URL (supports various identity provider patterns)
        if '/oidc' in self.config.oauth_authorization_endpoint:
            # Identity provider with OIDC endpoint pattern
            authorization_server_base = self.config.oauth_authorization_endpoint.split('/oidc')[0]
        else:
            # Standard OAuth endpoint pattern
            authorization_server_base = self.config.oauth_authorization_endpoint.split('/oauth')[0]
        
        return {
            "resource": self.config.resource_server_url,
            "authorization_servers": [
                {
                    "authorization_server": authorization_server_base,
                    "scopes_supported": self.config.all_scopes,
                    "bearer_methods_supported": ["header"],
                    "resource_documentation": f"{self.config.resource_server_url}/docs",
                    "resource_policy_uri": f"{self.config.resource_server_url}/policy"
                }
            ],
            "resource_server": self.config.resource_server_url,
            "resource_documentation": f"{self.config.resource_server_url}/docs"
        }
    
    def get_authorization_server_metadata(self) -> Dict[str, Any]:
        """Generate Authorization Server Metadata document.
        
        Returns:
            Dictionary containing authorization server metadata per RFC 8414
        """
        # Check if this is an external identity provider with OIDC support
        if '/oidc' in self.config.oauth_authorization_endpoint:
            # External identity provider with OIDC endpoint
            base_url = self.config.oauth_authorization_endpoint.split('/oidc')[0]
            
            return {
                "issuer": self.config.identity_discovery_url or base_url,
                "authorization_endpoint": self.config.oauth_authorization_endpoint,
                "token_endpoint": self.config.oauth_token_endpoint,
                "jwks_uri": self.config.identity_jwks_uri,
                "scopes_supported": self.config.all_scopes + ["openid", "profile", "email", "offline_access"],
                "response_types_supported": ["code", "id_token", "code id_token"],
                "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
                "id_token_signing_alg_values_supported": ["RS256"],
                "response_modes_supported": ["query", "fragment"],
                "subject_types_supported": ["public"],
                "userinfo_endpoint": f"{base_url}/oidc/userinfo"
            }
        else:
            # Standard OAuth server
            base_url = self.config.oauth_authorization_endpoint.split('/oauth')[0]
            
            return {
                "issuer": base_url,
                "authorization_endpoint": self.config.oauth_authorization_endpoint,
                "token_endpoint": self.config.oauth_token_endpoint,
                "jwks_uri": self.config.identity_jwks_uri,
                "scopes_supported": self.config.all_scopes + ["openid", "profile", "email"],
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "client_credentials"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
                "registration_endpoint": f"{base_url}/oauth/register",
                "response_modes_supported": ["query"],
                "id_token_signing_alg_values_supported": ["RS256"],
                "subject_types_supported": ["public"],
                "userinfo_endpoint": f"{base_url}/oauth/userinfo"
            }
    
    def generate_client_id_metadata_document(self, client_id: str, redirect_uris: list) -> Dict[str, Any]:
        """Generate Client ID Metadata Document (CIMD).
        
        Args:
            client_id: The client identifier
            redirect_uris: List of allowed redirect URIs
            
        Returns:
            Dictionary containing client metadata
        """
        client_metadata = {
            "client_id": client_id,
            "client_name": "MCP Client",
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": self.config.oauth_scope,
            "token_endpoint_auth_method": "client_secret_basic"
        }
        
        # Store client registration
        self._client_registrations[client_id] = client_metadata
        logger.info(f"Generated CIMD for client: {client_id}")
        
        return client_metadata
    
    async def register_client_dynamically(self, registration_request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle dynamic client registration (DCR).
        
        Args:
            registration_request: Client registration request data
            
        Returns:
            Dictionary containing client registration response
        """
        # Generate client credentials
        client_id = f"mcp_client_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)
        
        client_metadata = {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": registration_request.get("client_name", "MCP Client"),
            "redirect_uris": registration_request.get("redirect_uris", [self.config.oauth_redirect_uri]),
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": registration_request.get("scope", self.config.oauth_scope),
            "token_endpoint_auth_method": "client_secret_basic"
        }
        
        # Store client registration
        self._client_registrations[client_id] = client_metadata
        logger.info(f"Dynamically registered client: {client_id}")
        
        return client_metadata
    
    def build_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
        code_challenge: str,
        code_challenge_method: str = "S256"
    ) -> str:
        """Build OAuth authorization URL.
        
        Args:
            client_id: OAuth client ID
            redirect_uri: Redirect URI after authorization
            scope: Requested scopes
            state: State parameter for CSRF protection
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE challenge method
            
        Returns:
            Authorization URL string
        """
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "resource": self.config.resource_server_url
        }
        
        encoded_params = urllib.parse.urlencode(params)
        auth_url = f"{self.config.oauth_authorization_endpoint}?{encoded_params}"
        
        logger.info(f"Built authorization URL for client {client_id}")
        return auth_url
    
    async def exchange_code_for_token(
        self,
        authorization_code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token.
        
        Args:
            authorization_code: Authorization code from callback
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: Original redirect URI
            code_verifier: PKCE code verifier
            
        Returns:
            Token response dictionary
            
        Raises:
            HTTPException: If token exchange fails
        """
        token_data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.oauth_token_endpoint,
                    data=token_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Token exchange failed: {response.text}"
                    )
                
                token_response = response.json()
                logger.info(f"Successfully exchanged code for token (client: {client_id})")
                
                return token_response
                
        except httpx.RequestError as e:
            logger.error(f"Network error during token exchange: {e}")
            raise HTTPException(
                status_code=503,
                detail="Unable to contact authorization server"
            )
    
    def validate_client_credentials(self, client_id: str, client_secret: Optional[str] = None) -> bool:
        """Validate client credentials against registered clients.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret (optional for public clients)
            
        Returns:
            True if credentials are valid, False otherwise
        """
        if client_id not in self._client_registrations:
            logger.warning(f"Unknown client ID: {client_id}")
            return False
            
        client_data = self._client_registrations[client_id]
        
        # For confidential clients, verify secret
        if "client_secret" in client_data:
            if client_secret != client_data["client_secret"]:
                logger.warning(f"Invalid client secret for client: {client_id}")
                return False
                
        logger.debug(f"Valid client credentials for: {client_id}")
        return True
    
    def get_client_metadata(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client metadata by client ID.
        
        Args:
            client_id: OAuth client ID
            
        Returns:
            Client metadata dictionary or None if not found
        """
        return self._client_registrations.get(client_id)
    
    def generate_www_authenticate_header(self, error: str = None, error_description: str = None) -> str:
        """Generate WWW-Authenticate header for 401 responses per MCP OAuth spec.
        
        Args:
            error: OAuth error code
            error_description: Human-readable error description
            
        Returns:
            WWW-Authenticate header value
        """
        # Per MCP OAuth spec, include resource_metadata parameter
        resource_metadata_url = f"{self.config.resource_server_url}/.well-known/oauth-protected-resource"
        
        auth_params = [f'realm="{self.config.realm}"']
        auth_params.append(f'resource="{self.config.resource_server_url}"')
        auth_params.append(f'resource_metadata="{resource_metadata_url}"')  # MCP OAuth required
        
        if error:
            auth_params.append(f'error="{error}"')
        if error_description:
            auth_params.append(f'error_description="{error_description}"')
            
        return f"Bearer {', '.join(auth_params)}"