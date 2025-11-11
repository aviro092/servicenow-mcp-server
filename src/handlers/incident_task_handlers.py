"""Simplified MCP tool handlers for incident task management."""

import logging
from typing import Optional

from auth.decorators import requires_scope
from config import get_auth_config
from container import get_container
from tools.incident_task_tools import format_incident_task_display, get_incident_task_fields_info

logger = logging.getLogger(__name__)
auth_config = get_auth_config()


@requires_scope(auth_config.incident_task_read_scope)
async def get_incident_task(
    incident_task_number: str
) -> str:
    """Get incident task record details by task number.
    
    This tool retrieves comprehensive details about a ServiceNow incident task,
    including the parent incident information, task details, assignment, and status.
    
    Args:
        incident_task_number: The incident task number (e.g., TASK0133364)
        
    Returns:
        Formatted incident task details including:
        - Basic information (task number, incident number, severity, state)
        - Descriptions (incident and task descriptions)
        - Assignment details (group, individual)
        - Technical information (configuration item)
        - Timestamps (created, updated, closed)
        - Work notes and comments
        - Direct URL to the task in ServiceNow
    """
    logger.info(f"Fetching incident task details for: {incident_task_number}")
    
    try:
        container = get_container()
        tools = await container.get_incident_task_tools()
        task_data = await tools.get_incident_task(incident_task_number)
        
        # Check for errors in the response
        if "error" in task_data:
            error_msg = task_data["error"]
            error_type = task_data.get("error_type", "unknown")
            
            if error_type == "not_found":
                logger.warning(f"Incident task {incident_task_number} not found")
            else:
                logger.error(f"Error fetching incident task {incident_task_number}: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format the incident task data for display
        formatted_result = format_incident_task_display(task_data["incident_task"])
        logger.info(f"Successfully retrieved incident task data for: {incident_task_number}")
        
        return formatted_result
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error fetching incident task {incident_task_number}: {e}")
        return f"Error: {error_msg}"


@requires_scope(auth_config.incident_task_read_scope)
async def list_incident_task_fields() -> str:
    """List all available incident task fields and their descriptions.
    
    Returns:
        Formatted list of incident task fields with descriptions and examples
    """
    return get_incident_task_fields_info()


@requires_scope(auth_config.incident_task_write_scope)
async def update_incident_task(
    incident_task_number: str,
    short_description: str,
    state: int,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    assignment_group: Optional[str] = None,
    assigned_to: Optional[str] = None
) -> str:
    """Update incident task record by task number.
    
    Updates an existing ServiceNow incident task with new values.
    Short description and state are required; all other fields are optional.
    
    Args:
        incident_task_number: The incident task number to update (e.g., TASK0133364)
        short_description: Incident task short description - REQUIRED (max 120 chars)
        state: Incident task current state - REQUIRED (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)
        description: Incident task description details (max 4000 chars)
        priority: Priority level (1=Critical, 2=High, 3=Medium, 4=Low)
        assignment_group: Assignment Group mapped to sys_user_group table entries
        assigned_to: Assigned user details mapped to sys_user table entries
        
    Returns:
        Success message with updated incident task details or error message
    """
    logger.info(f"Updating incident task: {incident_task_number}")
    
    try:
        container = get_container()
        tools = await container.get_incident_task_tools()
        
        result = await tools.update_incident_task(
            incident_task_number=incident_task_number,
            short_description=short_description,
            state=state,
            description=description,
            priority=priority,
            assignment_group=assignment_group,
            assigned_to=assigned_to
        )
        
        # Check for errors in the response
        if "error" in result:
            error_msg = result["error"]
            error_type = result.get("error_type", "unknown")
            
            if error_type == "not_found":
                logger.warning(f"Incident task {incident_task_number} not found for update")
            elif error_type == "validation_error":
                logger.warning(f"Validation error updating incident task {incident_task_number}: {error_msg}")
            else:
                logger.error(f"Error updating incident task {incident_task_number}: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format success response
        if result.get("success"):
            updated_task = result.get("updated_incident_task", {})
            message = result.get("message", f"Incident task {incident_task_number} updated successfully")
            
            # Format the updated incident task data for display
            if updated_task:
                formatted_result = format_incident_task_display(updated_task)
                response = f"{message}\n\nUpdated Incident Task Details:\n{formatted_result}"
            else:
                response = message
            
            logger.info(f"Successfully updated incident task: {incident_task_number}")
            return response
        else:
            return f"Error: Update failed for incident task {incident_task_number}"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error updating incident task {incident_task_number}: {e}")
        return f"Error: {error_msg}"


@requires_scope(auth_config.incident_task_write_scope)
async def create_incident_task(
    incident_number: str,
    short_description: str,
    service_name: str,
    company_name: str,
    configuration_item: str,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    assignment_group: Optional[str] = None,
    assigned_to: Optional[str] = None
) -> str:
    """Create a new incident task record.
    
    Creates a new ServiceNow incident task for a specified incident.
    Required fields: incident_number, short_description, service_name, company_name, configuration_item.
    
    Args:
        incident_number: Parent Incident Number - REQUIRED (e.g., INC0012345)
        short_description: Incident task short description - REQUIRED (max 120 chars)
        service_name: Agreement Id mapped to cmdb_ci_service table - REQUIRED
        company_name: Incident task associated account details - REQUIRED
        configuration_item: Configuration item mapped to cmdb_ci table entry - REQUIRED
        description: Incident task description details (max 4000 chars)
        priority: Priority level (1=Critical, 2=High, 3=Medium, 4=Low)
        assignment_group: Assignment Group mapped to sys_user_group table entries
        assigned_to: Assigned user details mapped to sys_user table entries
        
    Returns:
        Success message with created incident task details or error message
    """
    logger.info(f"Creating new incident task")
    
    try:
        container = get_container()
        tools = await container.get_incident_task_tools()
        
        result = await tools.create_incident_task(
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
        
        # Check for errors in the response
        if "error" in result:
            error_msg = result["error"]
            error_type = result.get("error_type", "unknown")
            
            if error_type == "validation_error":
                logger.warning(f"Validation error creating incident task: {error_msg}")
            else:
                logger.error(f"Error creating incident task: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format success response
        if result.get("success"):
            created_task = result.get("created_incident_task", {})
            task_number = result.get("task_number", "Unknown")
            message = result.get("message", f"Incident task {task_number} created successfully")
            
            # Format the created incident task data for display
            if created_task:
                formatted_result = format_incident_task_display(created_task)
                response = f"{message}\n\nCreated Incident Task Details:\n{formatted_result}"
            else:
                response = message
            
            logger.info(f"Successfully created incident task: {task_number}")
            return response
        else:
            return "Error: Incident task creation failed"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error creating incident task: {e}")
        return f"Error: {error_msg}"