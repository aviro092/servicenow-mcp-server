"""Dependency injection container for ServiceNow MCP Server."""

import asyncio
from typing import Optional
import logging

from api import ServiceNowClient
from config import get_servicenow_config
from tools.incident_tools import IncidentTools
from tools.change_request_tools import ChangeRequestTools
from tools.incident_task_tools import IncidentTaskTools

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Dependency injection container for managing service instances."""
    
    def __init__(self):
        """Initialize the service container."""
        self._config = get_servicenow_config()
        self._client: Optional[ServiceNowClient] = None
        self._incident_tools: Optional[IncidentTools] = None
        self._change_request_tools: Optional[ChangeRequestTools] = None
        self._incident_task_tools: Optional[IncidentTaskTools] = None
        self._client_lock = asyncio.Lock()
        
    async def get_client(self) -> ServiceNowClient:
        """Get or create ServiceNow client instance."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    logger.debug("Creating new ServiceNow client instance")
                    self._client = ServiceNowClient(self._config)
        return self._client
    
    async def get_incident_tools(self) -> IncidentTools:
        """Get or create incident tools instance."""
        if self._incident_tools is None:
            client = await self.get_client()
            self._incident_tools = IncidentTools(client)
            logger.debug("Created incident tools instance")
        return self._incident_tools
    
    async def get_change_request_tools(self) -> ChangeRequestTools:
        """Get or create change request tools instance."""
        if self._change_request_tools is None:
            client = await self.get_client()
            self._change_request_tools = ChangeRequestTools(client)
            logger.debug("Created change request tools instance")
        return self._change_request_tools
    
    async def get_incident_task_tools(self) -> IncidentTaskTools:
        """Get or create incident task tools instance."""
        if self._incident_task_tools is None:
            client = await self.get_client()
            self._incident_task_tools = IncidentTaskTools(client)
            logger.debug("Created incident task tools instance")
        return self._incident_task_tools
    
    async def close(self) -> None:
        """Close all service instances and cleanup resources."""
        if self._client:
            await self._client.close()
            logger.debug("Closed ServiceNow client")
        
        # Reset all instances
        self._client = None
        self._incident_tools = None
        self._change_request_tools = None
        self._incident_task_tools = None


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get the global service container instance."""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


async def cleanup_container() -> None:
    """Cleanup the global container and all its resources."""
    global _container
    if _container:
        await _container.close()
        _container = None