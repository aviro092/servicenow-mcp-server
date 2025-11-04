"""Configuration management for ServiceNow MCP Server."""

import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class ServiceNowConfig(BaseSettings):
    """ServiceNow API configuration."""
    
    base_url: str = Field(
        ...,
        description="ServiceNow instance base URL (e.g., https://yourinstance.service-now.com)"
    )
    
    client_id: str = Field(
        ...,
        description="ServiceNow OAuth client ID"
    )
    
    client_secret: str = Field(
        ...,
        description="ServiceNow OAuth client secret"
    )
    
    token_endpoint: Optional[str] = Field(
        None,
        description="OAuth token endpoint (defaults to /oauth_token.do)"
    )
    
    api_version: str = Field(
        "v1",
        description="ServiceNow API version"
    )
    
    api_namespace: str = Field(
        "x_dusal_cmspapi",
        description="ServiceNow API namespace"
    )
    
    timeout: int = Field(
        30,
        description="API request timeout in seconds"
    )
    
    max_retries: int = Field(
        3,
        description="Maximum number of retry attempts for failed requests"
    )
    
    verify_ssl: bool = Field(
        True,
        description="Verify SSL certificates"
    )
    
    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base URL is properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")
    
    @property
    def api_base_path(self) -> str:
        """Construct the full API base path."""
        return f"{self.base_url}/api/{self.api_namespace}/{self.api_version}"
    
    @property
    def incident_endpoint(self) -> str:
        """Get the incident endpoint URL."""
        return f"{self.api_base_path}/itsm/incident"
    
    @property
    def oauth_token_url(self) -> str:
        """Get the OAuth token endpoint URL."""
        if self.token_endpoint:
            return f"{self.base_url}{self.token_endpoint}"
        return f"{self.base_url}/oauth_token.do"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "SERVICENOW_",
        "extra": "ignore"
    }


class ServerConfig(BaseSettings):
    """MCP Server configuration."""
    
    server_name: str = Field(
        "servicenow-mcp",
        description="Name of the MCP server"
    )
    
    log_level: str = Field(
        "INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    enable_debug: bool = Field(
        False,
        description="Enable debug mode"
    )
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "MCP_",
        "extra": "ignore"
    }


def get_servicenow_config() -> ServiceNowConfig:
    """Get ServiceNow configuration instance."""
    return ServiceNowConfig()


class MCPAuthConfig(BaseSettings):
    """MCP Bearer Token authentication configuration."""
    
    # Authentication Enable/Disable
    enable_auth: bool = Field(
        False,
        description="Enable Bearer Token authentication for MCP server"
    )
    
    # Authentication Mode
    auth_mode: str = Field(
        "mock",
        description="Authentication mode: 'mock' or 'identity-provider'"
    )
    
    # Identity Provider Configuration
    identity_jwks_uri: str = Field(
        "https://example.com/jwks",
        description="Identity provider JWKS URI for token verification"
    )
    
    identity_token_url: Optional[str] = Field(
        None,
        description="Identity provider token endpoint URL"
    )
    
    identity_discovery_url: Optional[str] = Field(
        None,
        description="Identity provider OIDC discovery URL"
    )
    
    # API Configuration
    api_identifier: str = Field(
        "ServiceNowMCPServerAPI",
        description="API identifier from identity provider"
    )
    
    # ServiceNow MCP Scopes
    incident_read_scope: str = Field(
        "servicenow.incident.read",
        description="Scope for reading incidents, searching, and listing fields"
    )
    
    incident_write_scope: str = Field(
        "servicenow.incident.write",
        description="Scope for creating and updating incidents"
    )
    
    # Mock Token Configuration
    mock_tokens: list[str] = Field(
        default_factory=lambda: [
            "valid_auth_token", "VALID_AUTH_TOKEN", "mock_token",
            "VALID_READ_SCOPE_TOKEN", "VALID_WRITE_SCOPE_TOKEN", 
            "MOCK_TOKEN", "test_token", "valid_token", "bearer_token",
            "servicenow_token"
        ],
        description="Valid mock tokens for testing"
    )
    
    @property
    def all_scopes(self) -> list[str]:
        """Get all ServiceNow MCP scopes."""
        return [
            self.incident_read_scope,
            self.incident_write_scope
        ]
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "MCP_AUTH_",
        "extra": "ignore"
    }


def get_server_config() -> ServerConfig:
    """Get server configuration instance."""
    return ServerConfig()


def get_auth_config() -> MCPAuthConfig:
    """Get authentication configuration instance."""
    return MCPAuthConfig()