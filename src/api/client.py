"""ServiceNow API client implementation."""

import asyncio
import logging
import time
from typing import Any, Dict, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log,
)

from config import ServiceNowConfig
from .exceptions import (
    ServiceNowAPIError,
    ServiceNowAuthError,
    ServiceNowNotFoundError,
    ServiceNowRateLimitError,
)

logger = logging.getLogger(__name__)


class ServiceNowClient:
    """ServiceNow API client for making authenticated requests with OAuth2."""
    
    def __init__(self, config: Optional[ServiceNowConfig] = None):
        """Initialize the ServiceNow client.
        
        Args:
            config: ServiceNow configuration. If None, will load from environment.
        """
        self.config = config or ServiceNowConfig()
        self._client = None
        self._oauth_client = None
        self._access_token = None
        self._token_expires_at = 0
        self._token_lock = asyncio.Lock()
        
    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        async with self._token_lock:
            # Check if current token is still valid (with 60 second buffer)
            if self._access_token and time.time() < (self._token_expires_at - 60):
                return self._access_token
            
            logger.debug("Requesting new OAuth2 access token")
            
            try:
                # Request new token using client credentials flow
                async with httpx.AsyncClient(verify=self.config.verify_ssl) as client:
                    response = await client.post(
                        self.config.oauth_token_url,
                        data={
                            "grant_type": "client_credentials",
                            "client_id": self.config.client_id,
                            "client_secret": self.config.client_secret,
                        },
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Accept": "application/json",
                        },
                        timeout=httpx.Timeout(30.0),
                    )
                    
                    if response.status_code == 401:
                        raise ServiceNowAuthError(
                            "OAuth2 authentication failed: Invalid client credentials",
                            status_code=401
                        )
                    
                    response.raise_for_status()
                    token_data = response.json()
                    
                    self._access_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 1800)  # Default 30 minutes
                    self._token_expires_at = time.time() + expires_in
                    
                    logger.info(f"OAuth2 token obtained successfully (expires in {expires_in}s)")
                    return self._access_token
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error getting OAuth2 token: {e}")
                raise ServiceNowAuthError(
                    f"Failed to get OAuth2 token: {e}",
                    status_code=e.response.status_code if e.response else None
                )
            except Exception as e:
                if isinstance(e, ServiceNowAuthError):
                    raise
                logger.error(f"Error getting OAuth2 token: {e}")
                raise ServiceNowAuthError(f"OAuth2 token request failed: {str(e)}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with current auth headers."""
        token = await self._get_access_token()
        
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout),
                verify=self.config.verify_ssl,
            )
        
        # Update authorization header with current token
        self._client.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        
        return self._client
    
    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the ServiceNow API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data
            
        Returns:
            Response data as dictionary
            
        Raises:
            ServiceNowAPIError: For various API errors
        """
        client = await self._get_client()
        
        try:
            logger.debug(f"Making {method} request to {endpoint}")
            
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
            )
            
            logger.debug(f"{method} {endpoint} - Status: {response.status_code}")
            
            # Handle different status codes
            if response.status_code == 401:
                logger.warning(f"Authentication failed for request to {endpoint}")
                raise ServiceNowAuthError(
                    "Authentication failed. Please check your OAuth2 credentials.",
                    status_code=response.status_code,
                )
            elif response.status_code == 404:
                logger.warning(f"Resource not found: {endpoint}")
                raise ServiceNowNotFoundError(
                    f"Resource not found: {endpoint}",
                    status_code=response.status_code,
                )
            elif response.status_code == 429:
                logger.warning(f"Rate limit exceeded for request to {endpoint}")
                raise ServiceNowRateLimitError(
                    "Rate limit exceeded. Please try again later.",
                    status_code=response.status_code,
                )
            elif response.status_code >= 400:
                error_data = None
                try:
                    error_data = response.json()
                except Exception:
                    pass
                
                logger.error(f"API error {response.status_code} for {endpoint}: {response.text}")
                raise ServiceNowAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                    response_data=error_data,
                )
            
            response.raise_for_status()
            logger.debug(f"Successfully completed request to {endpoint}")
            return response.json()
            
        except httpx.TransportError as e:
            logger.error(f"Network error making request to {endpoint}: {e}")
            raise ServiceNowAPIError(f"Network error: {str(e)}")
        except Exception as e:
            if isinstance(e, ServiceNowAPIError):
                raise
            logger.error(f"Unexpected error making request to {endpoint}: {e}")
            raise ServiceNowAPIError(f"Unexpected error: {str(e)}")
    
    async def get_incident(self, incident_number: str) -> Dict[str, Any]:
        """Get incident record details by incident number.
        
        Args:
            incident_number: The incident number (e.g., INC654321)
            
        Returns:
            Incident record data
            
        Raises:
            ServiceNowNotFoundError: If incident not found
            ServiceNowAPIError: For other API errors
        """
        endpoint = f"{self.config.incident_endpoint}/{incident_number}"
        logger.info(f"Fetching incident: {incident_number}")
        
        try:
            response = await self._make_request("GET", endpoint)
            return response.get("result", response)
        except ServiceNowNotFoundError:
            logger.warning(f"Incident not found: {incident_number}")
            raise ServiceNowNotFoundError(f"Incident {incident_number} not found")
        except Exception as e:
            logger.error(f"Error fetching incident {incident_number}: {e}")
            raise
    
    async def update_incident(self, incident_number: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update incident record by incident number.
        
        Args:
            incident_number: The incident number (e.g., INC654321)
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated incident record data
            
        Raises:
            ServiceNowNotFoundError: If incident not found
            ServiceNowAPIError: For other API errors
        """
        endpoint = f"{self.config.incident_endpoint}/{incident_number}"
        logger.info(f"Updating incident: {incident_number}")
        
        try:
            response = await self._make_request("PUT", endpoint, json_data=update_data)
            return response.get("result", response)
        except ServiceNowNotFoundError:
            logger.warning(f"Incident not found for update: {incident_number}")
            raise ServiceNowNotFoundError(f"Incident {incident_number} not found")
        except Exception as e:
            logger.error(f"Error updating incident {incident_number}: {e}")
            raise
    
    async def create_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new incident record.
        
        Args:
            incident_data: Dictionary containing incident creation data
            
        Returns:
            Created incident record data
            
        Raises:
            ServiceNowAPIError: For API errors
        """
        endpoint = self.config.incident_endpoint
        logger.info("Creating new incident")
        
        try:
            response = await self._make_request("POST", endpoint, json_data=incident_data)
            return response.get("result", response)
        except Exception as e:
            logger.error(f"Error creating incident: {e}")
            raise
    
    async def search_incidents(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search incident records based on query parameters.
        
        Args:
            search_params: Dictionary containing search parameters
            
        Returns:
            Search results with list of matching incidents
            
        Raises:
            ServiceNowAPIError: For API errors
        """
        endpoint = self.config.incident_endpoint
        logger.info(f"Searching incidents with parameters: {search_params}")
        
        try:
            response = await self._make_request("GET", endpoint, params=search_params)
            return response.get("result", response)
        except Exception as e:
            logger.error(f"Error searching incidents: {e}")
            raise
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()