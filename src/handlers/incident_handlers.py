"""MCP tool handlers for incident management."""

import logging
from typing import Optional

from auth.scope_validator import get_current_user, require_scope
from config import get_auth_config
from container import get_container
from tools.incident_tools import format_incident_display, get_incident_fields_info

logger = logging.getLogger(__name__)
auth_config = get_auth_config()


async def get_incident(
    incident_number: str
) -> str:
    """Get incident record details by incident number.
    
    This tool retrieves comprehensive details about a ServiceNow incident,
    including its status, assignment, description, and associated tasks.
    
    Args:
        incident_number: The incident number (e.g., INC654321)
        
    Returns:
        Formatted incident details including:
        - Basic information (number, state, priority, description)
        - Assignment details (group, individual)
        - Timestamps (created, modified, closed)
        - Associated incident tasks
        - Resolution information (if resolved)
        - Comments and notes
    """
    # Check authentication and authorization
    from auth.scope_validator import check_scope_access
    user = await check_scope_access(auth_config.incident_read_scope)
    
    logger.info(f"Fetching incident details for: {incident_number} (user: {user.claims.get('sub', 'unknown')})")
    
    try:
        container = get_container()
        tools = await container.get_incident_tools()
        incident_data = await tools.get_incident(incident_number)
        
        # Check for errors in the response
        if "error" in incident_data:
            error_msg = incident_data["error"]
            error_type = incident_data.get("error_type", "unknown")
            
            if error_type == "not_found":
                logger.warning(f"Incident {incident_number} not found")
            else:
                logger.error(f"Error fetching incident {incident_number}: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format the incident data for display
        formatted_result = format_incident_display(incident_data)
        logger.info(f"Successfully retrieved incident data for: {incident_number}")
        
        return formatted_result
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error fetching incident {incident_number}: {e}")
        return f"Error: {error_msg}"


async def list_incident_fields() -> str:
    """List all available incident fields and their descriptions.
    
    Returns:
        Formatted list of incident fields with descriptions and examples
    """
    # Check authentication and authorization
    from auth.scope_validator import check_scope_access
    user = await check_scope_access(auth_config.incident_read_scope)
    
    return get_incident_fields_info()


async def update_incident(
    incident_number: str,
    state: Optional[int] = None,
    impact: Optional[int] = None,
    urgency: Optional[int] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    short_description: Optional[str] = None,
    description: Optional[str] = None,
    holdreason: Optional[str] = None,
    service_impacting: Optional[str] = None,
    comments: Optional[str] = None,
    notes: Optional[str] = None,
    customer_reference_id: Optional[str] = None
) -> str:
    """Update incident record by incident number.
    
    Updates an existing ServiceNow incident with new values.
    All fields are optional except incident_number.
    
    Args:
        incident_number: The incident number to update (e.g., INC654321)
        state: Incident state (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)
        impact: Impact level (1=Critical, 2=High, 3=Medium, 4=Low)
        urgency: Urgency level (1=Critical, 2=High, 3=Medium, 4=Low)
        category: Category (e.g., "Performance")
        subcategory: Subcategory (e.g., "Slow Response")
        short_description: Brief description (max 120 chars)
        description: Full description (max 4000 chars)
        holdreason: Reason for hold state
        service_impacting: Service impact details
        comments: Add comments to incident
        notes: Add notes to incident
        customer_reference_id: Customer ticket ID
        
    Returns:
        Success message with updated incident details or error message
    """
    # Check authentication and authorization
    from auth.scope_validator import check_scope_access
    user = await check_scope_access(auth_config.incident_write_scope)
    
    logger.info(f"Updating incident: {incident_number} (user: {user.claims.get('sub', 'unknown')})")
    
    try:
        container = get_container()
        tools = await container.get_incident_tools()
        
        # Build update parameters, filtering out None values
        update_params = {
            k: v for k, v in {
                "state": state,
                "impact": impact,
                "urgency": urgency,
                "category": category,
                "subcategory": subcategory,
                "short_description": short_description,
                "description": description,
                "holdreason": holdreason,
                "service_impacting": service_impacting,
                "comments": comments,
                "notes": notes,
                "customer_reference_id": customer_reference_id,
            }.items() if v is not None
        }
        
        if not update_params:
            return "Error: No update fields provided. At least one field must be specified for update."
        
        result = await tools.update_incident(incident_number, **update_params)
        
        # Check for errors in the response
        if "error" in result:
            error_msg = result["error"]
            error_type = result.get("error_type", "unknown")
            
            if error_type == "not_found":
                logger.warning(f"Incident {incident_number} not found for update")
            elif error_type == "validation_error":
                logger.warning(f"Validation error updating incident {incident_number}: {error_msg}")
            else:
                logger.error(f"Error updating incident {incident_number}: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format success response
        if result.get("success"):
            updated_incident = result.get("updated_incident", {})
            message = result.get("message", f"Incident {incident_number} updated successfully")
            
            # Format the updated incident data for display
            if updated_incident:
                formatted_result = format_incident_display(updated_incident)
                response = f"{message}\n\nUpdated Incident Details:\n{formatted_result}"
            else:
                response = message
            
            logger.info(f"Successfully updated incident: {incident_number}")
            return response
        else:
            return f"Error: Update failed for incident {incident_number}"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error updating incident {incident_number}: {e}")
        return f"Error: {error_msg}"


async def create_incident(
    short_description: str,
    description: str,
    service_name: str,
    urgency: int,
    impact: Optional[int] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    configuration_item: Optional[str] = None,
    assigned_to: Optional[str] = None,
    assignment_group: Optional[str] = None,
    contact_type: Optional[str] = None,
    customer_reference_id: Optional[str] = None
) -> str:
    """Create a new incident record.
    
    Creates a new ServiceNow incident with the provided details.
    Required fields: short_description, description, service_name, urgency.
    
    Args:
        short_description: Brief description (max 120 chars) - REQUIRED
        description: Full description (max 4000 chars) - REQUIRED
        service_name: Service name mapped to cmdb_ci_service table - REQUIRED
        urgency: Urgency level (1=Critical, 2=High, 3=Medium, 4=Low) - REQUIRED
        impact: Impact level (1=Critical, 2=High, 3=Medium, 4=Low)
        category: Category (e.g., "Performance")
        subcategory: Subcategory (e.g., "Timeout")
        configuration_item: Configuration item sys_id
        assigned_to: Assigned user sys_id
        assignment_group: Assignment group
        contact_type: Interface type (e.g., "Self-Service")
        customer_reference_id: Customer ticket ID
        
    Returns:
        Success message with created incident details or error message
    """
    # Check authentication and authorization
    from auth.scope_validator import check_scope_access
    user = await check_scope_access(auth_config.incident_write_scope)
    
    logger.info(f"Creating new incident (user: {user.claims.get('sub', 'unknown')})")
    
    try:
        container = get_container()
        tools = await container.get_incident_tools()
        
        result = await tools.create_incident(
            short_description=short_description,
            description=description,
            service_name=service_name,
            urgency=urgency,
            impact=impact,
            category=category,
            subcategory=subcategory,
            configuration_item=configuration_item,
            assigned_to=assigned_to,
            assignment_group=assignment_group,
            contact_type=contact_type,
            customer_reference_id=customer_reference_id
        )
        
        # Check for errors in the response
        if "error" in result:
            error_msg = result["error"]
            error_type = result.get("error_type", "unknown")
            
            if error_type == "validation_error":
                logger.warning(f"Validation error creating incident: {error_msg}")
            else:
                logger.error(f"Error creating incident: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format success response
        if result.get("success"):
            created_incident = result.get("created_incident", {})
            incident_number = result.get("incident_number", "Unknown")
            message = result.get("message", f"Incident {incident_number} created successfully")
            
            # Format the created incident data for display
            if created_incident:
                formatted_result = format_incident_display(created_incident)
                response = f"{message}\n\nCreated Incident Details:\n{formatted_result}"
            else:
                response = message
            
            logger.info(f"Successfully created incident: {incident_number}")
            return response
        else:
            return "Error: Incident creation failed"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error creating incident: {e}")
        return f"Error: {error_msg}"


async def search_incidents(
    active: bool = True,
    requested_by: Optional[str] = None,
    company: Optional[str] = None,
    service_name: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    configuration_item: Optional[str] = None,
    state: Optional[int] = None,
    priority: Optional[int] = None,
    assignment_group: Optional[str] = None,
    assigned_to: Optional[str] = None
) -> str:
    """Search incident records based on query parameters.
    
    Searches for ServiceNow incidents matching the specified criteria.
    All search parameters are optional. If no parameters are provided, returns active incidents.
    
    Args:
        active: Select active records (default True)
        requested_by: Search by incident requestor name
        company: Search by company value
        service_name: Search by service name
        category: Search by category (e.g., "Performance")
        subcategory: Search by subcategory (e.g., "Timeout")
        configuration_item: Search by Configuration item sys_id
        state: Search by incident state (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)
        priority: Search by priority (1=Critical, 2=High, 3=Medium, 4=Low)
        assignment_group: Search by Assignment Group
        assigned_to: Search by assigned user
        
    Returns:
        Formatted list of matching incidents or error message
    """
    # Check authentication and authorization
    from auth.scope_validator import check_scope_access
    user = await check_scope_access(auth_config.incident_read_scope)
    
    logger.info(f"Searching incidents with specified criteria (user: {user.claims.get('sub', 'unknown')})")
    
    try:
        container = get_container()
        tools = await container.get_incident_tools()
        
        # Build search parameters, filtering out None values
        search_params = {
            k: v for k, v in {
                "active": active,
                "requested_by": requested_by,
                "company": company,
                "service_name": service_name,
                "category": category,
                "subcategory": subcategory,
                "configuration_item": configuration_item,
                "state": state,
                "priority": priority,
                "assignment_group": assignment_group,
                "assigned_to": assigned_to,
            }.items() if v is not None
        }
        
        result = await tools.search_incidents(**search_params)
        
        # Check for errors in the response
        if "error" in result:
            error_msg = result["error"]
            error_type = result.get("error_type", "unknown")
            
            if error_type == "validation_error":
                logger.warning(f"Validation error searching incidents: {error_msg}")
            else:
                logger.error(f"Error searching incidents: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format success response
        if result.get("success"):
            incidents = result.get("incidents", [])
            count = result.get("count", 0)
            search_criteria = result.get("search_criteria", {})
            message = result.get("message", f"Found {count} incidents")
            
            if count == 0:
                return f"No incidents found matching the search criteria.\n\nSearch Parameters:\n{search_criteria}"
            
            # Format search results
            lines = [f"Search Results: {message}"]
            lines.append("=" * 60)
            lines.append(f"Search Criteria: {search_criteria}")
            lines.append(f"Found {count} incident(s):")
            lines.append("=" * 60)
            
            # Show summary of each incident
            for i, incident in enumerate(incidents[:10], 1):  # Limit to first 10 for readability
                # Handle case where incident might be a string instead of dict
                if isinstance(incident, str):
                    lines.append(f"\n{i}. {incident}")
                    lines.append(f"   Note: Incident data returned as string format")
                elif isinstance(incident, dict):
                    lines.append(f"\n{i}. {incident.get('number', 'N/A')}")
                    lines.append(f"   State: {incident.get('state', 'N/A')}")
                    lines.append(f"   Priority: {incident.get('priority', 'N/A')}")
                    lines.append(f"   Requested By: {incident.get('requested_by', 'N/A')}")
                    lines.append(f"   Company: {incident.get('company', 'N/A')}")
                    lines.append(f"   Short Description: {incident.get('short_description', 'N/A')}")
                    lines.append(f"   Assignment Group: {incident.get('assignment_group', 'N/A')}")
                else:
                    lines.append(f"\n{i}. {str(incident)}")
                    lines.append(f"   Note: Unexpected incident data format: {type(incident)}")
            
            if count > 10:
                lines.append(f"\n... and {count - 10} more incidents")
                lines.append("\nNote: Only showing first 10 incidents for readability.")
                lines.append("Use more specific search criteria to narrow results.")
            
            response = "\n".join(lines)
            logger.info(f"Successfully found {count} incidents")
            return response
        else:
            return "Error: Search failed"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error searching incidents: {e}")
        return f"Error: {error_msg}"