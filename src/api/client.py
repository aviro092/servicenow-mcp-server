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

    async def search_change_requests(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search change request records based on query parameters.
        
        Args:
            search_params: Dictionary containing search parameters
            
        Returns:
            Search results with list of matching change requests
            
        Raises:
            ServiceNowAPIError: For API errors
            ServiceNowNotFoundError: When no change requests found
        """
        try:
            # Build query parameters
            params = {}
            for key, value in search_params.items():
                if value is not None:
                    params[key] = str(value).lower() if isinstance(value, bool) else str(value)
            
            logger.debug(f"Searching change requests with params: {params}")
            
            response = await self._make_request(
                "GET", 
                f"{self.config.api_base_path}/itsm/changerequest",
                params=params
            )
            
            # Handle different response formats
            if isinstance(response, dict):
                if "result" in response:
                    change_requests = response["result"]
                else:
                    change_requests = [response] if response else []
            elif isinstance(response, list):
                change_requests = response
            else:
                change_requests = []
            
            logger.info(f"Found {len(change_requests)} change requests")
            
            return {
                "success": True,
                "count": len(change_requests),
                "change_requests": change_requests,
                "search_criteria": search_params
            }
            
        except ServiceNowNotFoundError:
            # Return empty results instead of raising error
            logger.info("No change requests found matching criteria")
            return {
                "success": True,
                "count": 0,
                "change_requests": [],
                "search_criteria": search_params,
                "message": "No change requests found matching the search criteria"
            }
        except Exception as e:
            logger.error(f"Error searching change requests: {e}")
            raise

    async def get_change_request(self, changerequest_number: str) -> Dict[str, Any]:
        """Get a change request by its number.
        
        Args:
            changerequest_number: The change request number (e.g., CHG0035060)
            
        Returns:
            Change request details
            
        Raises:
            ServiceNowAPIError: For API errors
            ServiceNowNotFoundError: When change request not found
        """
        try:
            logger.debug(f"Fetching change request: {changerequest_number}")
            
            endpoint = f"{self.config.api_base_path}/itsm/changerequest/{changerequest_number}"
            response = await self._make_request("GET", endpoint)
            
            logger.info(f"Successfully retrieved change request: {changerequest_number}")
            return response
            
        except ServiceNowNotFoundError:
            logger.warning(f"Change request {changerequest_number} not found")
            raise
        except Exception as e:
            logger.error(f"Error fetching change request {changerequest_number}: {e}")
            raise

    async def update_change_request(self, changerequest_number: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a change request by its number.
        
        Args:
            changerequest_number: The change request number (e.g., CHG0035060)
            update_data: Dictionary containing update fields
            
        Returns:
            Update response with updated change request details
            
        Raises:
            ServiceNowAPIError: For API errors
            ServiceNowNotFoundError: When change request not found
        """
        try:
            logger.debug(f"Updating change request: {changerequest_number} with data: {update_data}")
            
            endpoint = f"{self.config.api_base_path}/itsm/changerequest/{changerequest_number}"
            
            # Convert boolean values to strings as ServiceNow expects
            processed_data = {}
            for key, value in update_data.items():
                if isinstance(value, bool):
                    processed_data[key] = str(value).lower()
                else:
                    processed_data[key] = value
            
            response = await self._make_request("PUT", endpoint, json=processed_data)
            
            logger.info(f"Successfully updated change request: {changerequest_number}")
            return response
            
        except ServiceNowNotFoundError:
            logger.warning(f"Change request {changerequest_number} not found for update")
            raise
        except Exception as e:
            logger.error(f"Error updating change request {changerequest_number}: {e}")
            raise

    async def approve_change_request(self, changerequest_number: str, approval_data: Dict[str, Any]) -> Dict[str, Any]:
        """Approve or reject a change request by its number.
        
        Args:
            changerequest_number: The change request number (e.g., CHG0035060)
            approval_data: Dictionary containing approval data including state and approver_email
            
        Returns:
            Approval response with status
            
        Raises:
            ServiceNowAPIError: For API errors
            ServiceNowNotFoundError: When change request not found
        """
        try:
            logger.debug(f"Processing approval for change request: {changerequest_number} with data: {approval_data}")
            
            endpoint = f"{self.config.api_base_path}/itsm/changerequest/{changerequest_number}"
            
            response = await self._make_request("PATCH", endpoint, json_data=approval_data)
            
            approval_state = approval_data.get('state', 'unknown')
            logger.info(f"Successfully {approval_state} change request: {changerequest_number}")
            return response
            
        except ServiceNowNotFoundError:
            logger.warning(f"Change request {changerequest_number} not found for approval")
            raise
        except Exception as e:
            logger.error(f"Error processing approval for change request {changerequest_number}: {e}")
            raise

    async def get_incident_task(self, incident_task_number: str) -> Dict[str, Any]:
        """Get incident task record details by task number.
        
        Args:
            incident_task_number: The incident task number (e.g., TASK0133364)
            
        Returns:
            Incident task record data
            
        Raises:
            ServiceNowNotFoundError: If incident task not found
            ServiceNowAPIError: For other API errors
        """
        endpoint = f"{self.config.api_base_path}/itsm/incident_task/{incident_task_number}"
        logger.info(f"Fetching incident task: {incident_task_number}")
        
        try:
            response = await self._make_request("GET", endpoint)
            return response.get("result", response)
        except ServiceNowNotFoundError:
            logger.warning(f"Incident task not found: {incident_task_number}")
            raise ServiceNowNotFoundError(f"Incident task {incident_task_number} not found")
        except Exception as e:
            logger.error(f"Error fetching incident task {incident_task_number}: {e}")
            raise

    async def update_incident_task(self, incident_task_number: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an incident task by its number.
        
        Args:
            incident_task_number: The incident task number (e.g., TASK0133364)
            update_data: Dictionary containing update fields
            
        Returns:
            Update response with updated incident task details
            
        Raises:
            ServiceNowAPIError: For API errors
            ServiceNowNotFoundError: When incident task not found
        """
        try:
            logger.debug(f"Updating incident task: {incident_task_number} with data: {update_data}")
            
            endpoint = f"{self.config.api_base_path}/itsm/incident_task/{incident_task_number}"
            
            response = await self._make_request("PUT", endpoint, json_data=update_data)
            
            logger.info(f"Successfully updated incident task: {incident_task_number}")
            return response
            
        except ServiceNowNotFoundError:
            logger.warning(f"Incident task {incident_task_number} not found for update")
            raise
        except Exception as e:
            logger.error(f"Error updating incident task {incident_task_number}: {e}")
            raise

    async def create_incident_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new incident task record.
        
        Args:
            task_data: Dictionary containing incident task creation data
            
        Returns:
            Created incident task record data
            
        Raises:
            ServiceNowAPIError: For API errors
        """
        endpoint = f"{self.config.api_base_path}/itsm/incident_task"
        logger.info("Creating new incident task")
        
        try:
            response = await self._make_request("POST", endpoint, json_data=task_data)
            return response.get("result", response)
        except Exception as e:
            logger.error(f"Error creating incident task: {e}")
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