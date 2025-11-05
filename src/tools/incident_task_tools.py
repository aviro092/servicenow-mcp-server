"""Incident Task management tools for ServiceNow MCP Server."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from api import ServiceNowClient

logger = logging.getLogger(__name__)


class IncidentTaskTools:
    """Tools for managing ServiceNow incident tasks."""
    
    def __init__(self, client: ServiceNowClient):
        """Initialize incident task tools with ServiceNow client.
        
        Args:
            client: ServiceNow API client instance
        """
        self.client = client
        
    async def get_incident_task(self, incident_task_number: str) -> Dict[str, Any]:
        """Get incident task details by task number.
        
        Args:
            incident_task_number: The incident task number (e.g., TASK0133364)
            
        Returns:
            Dictionary containing incident task details or error information
        """
        try:
            logger.info(f"Fetching incident task: {incident_task_number}")
            
            # Call the API client
            task_data = await self.client.get_incident_task(incident_task_number)
            
            logger.info(f"Successfully retrieved incident task: {incident_task_number}")
            
            return {
                "success": True,
                "incident_task": task_data,
                "task_number": incident_task_number
            }
            
        except Exception as e:
            from api.exceptions import ServiceNowNotFoundError
            
            if isinstance(e, ServiceNowNotFoundError):
                error_msg = f"Incident task '{incident_task_number}' not found"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "error_type": "not_found"
                }
            else:
                error_msg = f"Unexpected error fetching incident task: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    "error": error_msg,
                    "error_type": "unexpected_error"
                }

    async def update_incident_task(
        self,
        incident_task_number: str,
        short_description: str,
        state: int,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        assignment_group: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update incident task by task number.
        
        Args:
            incident_task_number: The incident task number to update (e.g., TASK0133364)
            short_description: Incident task short description - REQUIRED
            state: Incident task record current state - REQUIRED (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)
            description: Incident task description details
            priority: Incident task record priority value (1=Critical, 2=High, 3=Medium, 4=Low)
            assignment_group: Assignment Group mapped to sys_user_group table entries
            assigned_to: Assigned user details mapped to sys_user table entries
            
        Returns:
            Dictionary containing update results or error information
        """
        try:
            logger.info(f"Updating incident task: {incident_task_number}")
            
            # Import models here to avoid circular imports
            from models import IncidentTaskUpdateRequest
            
            # Validate input parameters
            update_request = IncidentTaskUpdateRequest(
                short_description=short_description,
                state=state,
                description=description,
                priority=priority,
                assignment_group=assignment_group,
                assigned_to=assigned_to
            )
            
            # Build update data dictionary
            update_data = update_request.model_dump(exclude_none=True)
            
            # Call the API client to update the incident task
            response = await self.client.update_incident_task(
                incident_task_number,
                update_data
            )
            
            # Check if response indicates success
            if response and not isinstance(response, dict):
                response = {"result": response}
            
            result = response.get("result", response)
            
            logger.info(f"Successfully updated incident task: {incident_task_number}")
            
            return {
                "success": True,
                "updated_incident_task": result,
                "task_number": incident_task_number,
                "message": f"Incident task {incident_task_number} updated successfully"
            }
            
        except ValueError as e:
            error_msg = f"Invalid update parameters: {str(e)}"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "error_type": "validation_error"
            }
        except Exception as e:
            from api.exceptions import ServiceNowNotFoundError
            
            if isinstance(e, ServiceNowNotFoundError):
                error_msg = f"Incident task '{incident_task_number}' not found"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "error_type": "not_found"
                }
            else:
                error_msg = f"Unexpected error updating incident task: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    "error": error_msg,
                    "error_type": "unexpected_error"
                }

    async def create_incident_task(
        self,
        incident_number: str,
        short_description: str,
        service_name: str,
        company_name: str,
        configuration_item: str,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        assignment_group: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new incident task.
        
        Args:
            incident_number: Parent Incident Number - REQUIRED
            short_description: Incident task short description - REQUIRED
            service_name: Agreement Id is mapped to cmdb_ci_service table - REQUIRED
            company_name: Incident task associated account details - REQUIRED
            configuration_item: Configuration item mapped to cmdb_ci table entry - REQUIRED
            description: Incident task description details
            priority: Incident task record priority value (1=Critical, 2=High, 3=Medium, 4=Low)
            assignment_group: Assignment Group mapped to sys_user_group table entries
            assigned_to: Assigned user details mapped to sys_user table entries
            
        Returns:
            Dictionary containing creation results or error information
        """
        try:
            logger.info("Creating new incident task")
            
            # Import models here to avoid circular imports
            from models import IncidentTaskCreateRequest
            
            # Validate input parameters
            create_request = IncidentTaskCreateRequest(
                incident_number=incident_number,
                short_description=short_description,
                service_name=service_name,
                company_name=company_name,
                configuration_item=configuration_item,
                description=description,
                priority=priority,
                assignment_group=assignment_group,
                assigned_to=assigned_to
            )
            
            # Build creation data dictionary
            task_data = create_request.model_dump(exclude_none=True)
            
            # Call the API client to create the incident task
            response = await self.client.create_incident_task(task_data)
            
            # Check if response indicates success
            if response and not isinstance(response, dict):
                response = {"result": response}
            
            result = response.get("result", response)
            task_number = result.get("task_number", "Unknown")
            
            logger.info(f"Successfully created incident task: {task_number}")
            
            return {
                "success": True,
                "created_incident_task": result,
                "task_number": task_number,
                "message": f"Incident task {task_number} created successfully"
            }
            
        except ValueError as e:
            error_msg = f"Invalid creation parameters: {str(e)}"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "error_type": "validation_error"
            }
        except Exception as e:
            error_msg = f"Unexpected error creating incident task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "error_type": "unexpected_error"
            }


def format_incident_task_display(incident_task: Dict[str, Any]) -> str:
    """Format an incident task for display.
    
    Args:
        incident_task: Incident task data from ServiceNow API
        
    Returns:
        Formatted string representation of the incident task
    """
    lines = []
    
    # Header
    task_number = incident_task.get("task_number", "Unknown")
    lines.append(f"Incident Task: {task_number}")
    lines.append("=" * 60)
    
    # Basic Information
    lines.append("\n📋 BASIC INFORMATION")
    lines.append("-" * 30)
    lines.append(f"Task Number: {incident_task.get('task_number', 'N/A')}")
    lines.append(f"Incident Number: {incident_task.get('incident_number', 'N/A')}")
    lines.append(f"State: {incident_task.get('state', 'N/A')}")
    lines.append(f"Severity: {incident_task.get('severity', 'N/A')}")
    lines.append(f"Priority: {incident_task.get('priority', 'N/A')}")
    
    # Descriptions
    lines.append("\n📄 DESCRIPTION")
    lines.append("-" * 30)
    
    incident_desc = incident_task.get("incident_short_description")
    if incident_desc:
        lines.append(f"Incident Description: {incident_desc}")
    
    task_desc = incident_task.get("task_short_description")
    if task_desc:
        lines.append(f"Task Description: {task_desc}")
    
    if incident_task.get("description"):
        lines.append(f"Full Description: {incident_task.get('description')}")
    
    # Assignment Information
    if incident_task.get("assignment_group") or incident_task.get("assigned_to"):
        lines.append("\n👥 ASSIGNMENT")
        lines.append("-" * 30)
        if incident_task.get("assignment_group"):
            lines.append(f"Assignment Group: {incident_task.get('assignment_group')}")
        if incident_task.get("assigned_to"):
            lines.append(f"Assigned To: {incident_task.get('assigned_to')}")
    
    # Technical Information
    if incident_task.get("configuration_item"):
        lines.append("\n🔧 TECHNICAL INFORMATION")
        lines.append("-" * 30)
        lines.append(f"Configuration Item: {incident_task.get('configuration_item')}")
    
    # Dates
    lines.append("\n📅 DATES")
    lines.append("-" * 30)
    lines.append(f"Created: {_format_date(incident_task.get('created'))}")
    if incident_task.get("updated_on"):
        lines.append(f"Updated: {_format_date(incident_task.get('updated_on'))}")
    if incident_task.get("closed_at"):
        lines.append(f"Closed: {_format_date(incident_task.get('closed_at'))}")
    
    # Comments and Work Notes
    if incident_task.get("work_notes") or incident_task.get("comments"):
        lines.append("\n💬 NOTES")
        lines.append("-" * 30)
        if incident_task.get("work_notes"):
            lines.append(f"Work Notes: {incident_task.get('work_notes')}")
        if incident_task.get("comments"):
            lines.append(f"Comments: {incident_task.get('comments')}")
    
    # Direct URL
    if incident_task.get("url"):
        lines.append("\n🔗 DIRECT LINK")
        lines.append("-" * 30)
        lines.append(f"URL: {incident_task.get('url')}")
    
    return "\n".join(lines)


def _format_date(date_str: Optional[str]) -> str:
    """Format a date string for display.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Formatted date string or N/A
    """
    if not date_str:
        return "N/A"
    
    # Return as-is for now, could add date parsing/formatting later
    return date_str


def get_incident_task_fields_info() -> str:
    """Get information about incident task fields.
    
    Returns:
        Formatted string with field descriptions
    """
    return """📋 INCIDENT TASK FIELDS REFERENCE
════════════════════════════════════════

BASIC FIELDS:
─────────────
• task_number: Task identifier (e.g., TASK0133364)
• incident_number: Parent incident number (e.g., INC0134292)
• state: Current state of the task
• severity: Severity level (1-4)
• priority: Priority level

DESCRIPTIVE FIELDS:
──────────────────
• incident_short_description: Parent incident description
• task_short_description: Task-specific description
• description: Full task description

TECHNICAL FIELDS:
────────────────
• configuration_item: CI sys_id from cmdb_ci table
• sys_id: System identifier

ASSIGNMENT FIELDS:
─────────────────
• assignment_group: Group responsible for task
• assigned_to: Individual assigned to task

TIMESTAMP FIELDS:
────────────────
• created: Task creation timestamp
• updated_on: Last update timestamp
• closed_at: Task closure timestamp

ADDITIONAL FIELDS:
─────────────────
• work_notes: Internal work notes
• comments: Customer-visible comments
• url: Direct link to task in ServiceNow

EXAMPLE USAGE:
─────────────
Get incident task details:
  task_number: "TASK0133364"

Response includes parent incident information,
task details, assignments, and timestamps."""