"""ServiceNow MCP Server built with FastMCP."""

import asyncio
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from api import ServiceNowClient, ServiceNowAPIError, ServiceNowNotFoundError
from config import get_servicenow_config, get_auth_config
from tools.incident_tools import (
    IncidentTools,
    format_incident_display,
    get_incident_fields_info
)
from tools.change_request_tools import (
    ChangeRequestTools,
    format_change_request_display,
    get_change_request_fields_info
)
from tools.incident_task_tools import (
    IncidentTaskTools,
    format_incident_task_display,
    get_incident_task_fields_info
)
from auth import require_scope

# Setup simple logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Create FastMCP server
server = FastMCP(
    name="servicenow-mcp",
    instructions="ServiceNow MCP server for incident management and API integration",
    version="0.1.0"
)

# Global client and tools instances
_client: ServiceNowClient = None
_incident_tools: IncidentTools = None
_change_request_tools: ChangeRequestTools = None
_incident_task_tools: IncidentTaskTools = None

# Get auth config for scopes
auth_config = get_auth_config()


@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """Health check endpoint for Docker health checks."""
    return PlainTextResponse("OK")


async def get_client() -> ServiceNowClient:
    """Get or create ServiceNow client instance."""
    global _client
    if _client is None:
        config = get_servicenow_config()
        _client = ServiceNowClient(config)
    return _client


async def get_incident_tools() -> IncidentTools:
    """Get or create incident tools instance."""
    global _incident_tools
    if _incident_tools is None:
        client = await get_client()
        _incident_tools = IncidentTools(client)
    return _incident_tools


async def get_change_request_tools() -> ChangeRequestTools:
    """Get or create change request tools instance."""
    global _change_request_tools
    if _change_request_tools is None:
        client = await get_client()
        _change_request_tools = ChangeRequestTools(client)
    return _change_request_tools


async def get_incident_task_tools() -> IncidentTaskTools:
    """Get or create incident task tools instance."""
    global _incident_task_tools
    if _incident_task_tools is None:
        client = await get_client()
        _incident_task_tools = IncidentTaskTools(client)
    return _incident_task_tools


@server.tool
@require_scope(auth_config.incident_read_scope)
async def get_incident(incident_number: str) -> str:
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
    logger.info(f"Fetching incident details for: {incident_number}")
    
    try:
        tools = await get_incident_tools()
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


@server.tool
@require_scope(auth_config.incident_read_scope)
async def list_incident_fields() -> str:
    """List all available incident fields and their descriptions.
    
    Returns:
        Formatted list of incident fields with descriptions and examples
    """
    return get_incident_fields_info()


@server.tool
@require_scope(auth_config.incident_write_scope)
async def update_incident(
    incident_number: str,
    state: int = None,
    impact: int = None,
    urgency: int = None,
    category: str = None,
    subcategory: str = None,
    short_description: str = None,
    description: str = None,
    holdreason: str = None,
    service_impacting: str = None,
    comments: str = None,
    notes: str = None,
    customer_reference_id: str = None
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
    logger.info(f"Updating incident: {incident_number}")
    
    try:
        tools = await get_incident_tools()
        
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


@server.tool
@require_scope(auth_config.incident_write_scope)
async def create_incident(
    short_description: str,
    description: str,
    service_name: str,
    urgency: int,
    impact: int = None,
    category: str = None,
    subcategory: str = None,
    configuration_item: str = None,
    assigned_to: str = None,
    assignment_group: str = None,
    contact_type: str = None,
    customer_reference_id: str = None
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
    logger.info("Creating new incident")
    
    try:
        tools = await get_incident_tools()
        
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


@server.tool
@require_scope(auth_config.incident_read_scope)
async def search_incidents(
    active: bool = True,
    requested_by: str = None,
    company: str = None,
    service_name: str = None,
    category: str = None,
    subcategory: str = None,
    configuration_item: str = None,
    state: int = None,
    priority: int = None,
    assignment_group: str = None,
    assigned_to: str = None
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
    logger.info("Searching incidents with specified criteria")
    
    try:
        tools = await get_incident_tools()
        
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


@server.tool
@require_scope(auth_config.change_request_read_scope)
async def search_change_requests(
    active: bool = True,
    requested_by: str = None,
    agreement_id: str = None,
    company: str = None,
    category: str = None,
    cmdb_ci: str = None,
    type: str = None,
    priority: int = None,
    risk: int = None,
    impact: int = None,
    state: int = None,
    assignment_group: str = None,
    assigned_to: str = None
) -> str:
    """Search change request records based on query parameters.
    
    Searches for ServiceNow change requests matching the specified criteria.
    All search parameters are optional. If no parameters are provided, returns active change requests.
    
    Args:
        active: Select active records (default True)
        requested_by: Search by Change Request's Requestor name
        agreement_id: Search by Change Request's Agreement Id
        company: Search by Change Request's Company
        category: Search by Change Request's Category
        cmdb_ci: Search by Change Request's CMDB CI
        type: Search by Change Request's type (Standard, Emergency, Normal)
        priority: Search by priority (1=Critical, 2=High, 3=Medium, 4=Low)
        risk: Search by risk (1=Very Low, 2=Low, 3=Medium, 4=High, 5=Very High)
        impact: Search by impact (1=Critical, 2=High, 3=Medium, 4=Low)
        state: Search by state (1=New, 2=Assess, 3=Authorize, 4=Scheduled, 5=Implement, 6=Review, 7=Closed, 8=Canceled)
        assignment_group: Search by Assignment Group
        assigned_to: Search by assigned user
        
    Returns:
        Formatted list of matching change requests or error message
    """
    logger.info("Searching change requests with specified criteria")
    
    try:
        tools = await get_change_request_tools()
        
        # Build search parameters, filtering out None values
        search_params = {
            k: v for k, v in {
                "active": active,
                "requested_by": requested_by,
                "agreement_id": agreement_id,
                "company": company,
                "category": category,
                "cmdb_ci": cmdb_ci,
                "type": type,
                "priority": priority,
                "risk": risk,
                "impact": impact,
                "state": state,
                "assignment_group": assignment_group,
                "assigned_to": assigned_to,
            }.items() if v is not None
        }
        
        result = await tools.search_change_requests(**search_params)
        
        # Check for errors in the response
        if "error" in result:
            error_msg = result["error"]
            error_type = result.get("error_type", "unknown")
            
            if error_type == "validation_error":
                logger.warning(f"Validation error searching change requests: {error_msg}")
            else:
                logger.error(f"Error searching change requests: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format success response
        if result.get("success"):
            change_requests = result.get("change_requests", [])
            count = result.get("count", 0)
            search_criteria = result.get("search_criteria", {})
            message = result.get("message", f"Found {count} change requests")
            
            if count == 0:
                return f"No change requests found matching the search criteria.\n\nSearch Parameters:\n{search_criteria}"
            
            # Format search results
            lines = [f"Search Results: {message}"]
            lines.append("=" * 60)
            lines.append(f"Search Criteria: {search_criteria}")
            lines.append(f"Found {count} change request(s):")
            lines.append("=" * 60)
            
            # Show summary of each change request
            for i, cr in enumerate(change_requests[:10], 1):  # Limit to first 10 for readability
                # Handle case where change request might be a string instead of dict
                if isinstance(cr, str):
                    lines.append(f"\n{i}. {cr}")
                    lines.append(f"   Note: Change request data returned as string format")
                elif isinstance(cr, dict):
                    lines.append(f"\n{i}. {cr.get('number', 'N/A')}")
                    lines.append(f"   State: {cr.get('state', 'N/A')}")
                    lines.append(f"   Type: {cr.get('type', 'N/A')}")
                    lines.append(f"   Priority: {cr.get('priority', 'N/A')}")
                    lines.append(f"   Risk: {cr.get('risk', 'N/A')}")
                    lines.append(f"   Requested By: {cr.get('requested_by', 'N/A')}")
                    lines.append(f"   Company: {cr.get('company', 'N/A')}")
                    lines.append(f"   Short Description: {cr.get('short_description', 'N/A')}")
                    lines.append(f"   Assignment Group: {cr.get('assignment_group', 'N/A')}")
                else:
                    lines.append(f"\n{i}. {str(cr)}")
                    lines.append(f"   Note: Unexpected change request data format: {type(cr)}")
            
            if count > 10:
                lines.append(f"\n... and {count - 10} more change requests")
                lines.append("\nNote: Only showing first 10 change requests for readability.")
                lines.append("Use more specific search criteria to narrow results.")
            
            response = "\n".join(lines)
            logger.info(f"Successfully found {count} change requests")
            return response
        else:
            return "Error: Search failed"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error searching change requests: {e}")
        return f"Error: {error_msg}"


@server.tool
@require_scope(auth_config.change_request_read_scope)
async def get_change_request(changerequest_number: str) -> str:
    """Get change request record details by change request number.
    
    This tool retrieves comprehensive details about a ServiceNow change request,
    including its status, assignment, description, plans, and associated information.
    
    Args:
        changerequest_number: The change request number (e.g., CHG0035060)
        
    Returns:
        Formatted change request details including:
        - Basic information (number, state, type, priority, risk, impact)
        - Request details (requested by, company, agreement)
        - Assignment information (group, individual)
        - Timestamps (created, start date, end date)
        - Description and plans (implementation, test, backout)
        - Technical information (CMDB CI, conflict status)
        - Work notes and comments
    """
    logger.info(f"Fetching change request details for: {changerequest_number}")
    
    try:
        tools = await get_change_request_tools()
        changerequest_data = await tools.get_change_request(changerequest_number)
        
        # Check for errors in the response
        if "error" in changerequest_data:
            error_msg = changerequest_data["error"]
            error_type = changerequest_data.get("error_type", "unknown")
            
            if error_type == "not_found":
                logger.warning(f"Change request {changerequest_number} not found")
            else:
                logger.error(f"Error fetching change request {changerequest_number}: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format the change request data for display
        formatted_result = format_change_request_display(changerequest_data["changerequest"])
        logger.info(f"Successfully retrieved change request data for: {changerequest_number}")
        
        return formatted_result
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error fetching change request {changerequest_number}: {e}")
        return f"Error: {error_msg}"


@server.tool
@require_scope(auth_config.change_request_read_scope)
async def list_change_request_fields() -> str:
    """List all available change request fields and their descriptions.
    
    Returns:
        Formatted list of change request fields with descriptions and examples
    """
    return get_change_request_fields_info()


@server.tool
@require_scope(auth_config.change_request_write_scope)
async def update_change_request(
    changerequest_number: str,
    company_name: str,
    description: str = None,
    comments: str = None,
    on_hold: bool = None,
    on_hold_reason: str = None,
    resolved: bool = None,
    customer_reference_id: str = None
) -> str:
    """Update change request record by change request number.
    
    Updates an existing ServiceNow change request with new values.
    Company name is required; all other fields are optional.
    
    Args:
        changerequest_number: The change request number to update (e.g., CHG0035060)
        company_name: Company name from company record - REQUIRED
        description: Description for change request
        comments: New comment to be added to change request
        on_hold: Whether to put change request on hold or not
        on_hold_reason: Reason for putting change request on hold
        resolved: Whether to mark change request as resolved or not
        customer_reference_id: Customer Change Request number
        
    Returns:
        Success message with updated change request details or error message
    """
    logger.info(f"Updating change request: {changerequest_number}")
    
    try:
        tools = await get_change_request_tools()
        
        # Build update parameters, filtering out None values
        update_params = {
            k: v for k, v in {
                "company_name": company_name,
                "description": description,
                "comments": comments,
                "on_hold": on_hold,
                "on_hold_reason": on_hold_reason,
                "resolved": resolved,
                "customer_reference_id": customer_reference_id,
            }.items() if v is not None
        }
        
        result = await tools.update_change_request(changerequest_number, **update_params)
        
        # Check for errors in the response
        if "error" in result:
            error_msg = result["error"]
            error_type = result.get("error_type", "unknown")
            
            if error_type == "not_found":
                logger.warning(f"Change request {changerequest_number} not found for update")
            elif error_type == "validation_error":
                logger.warning(f"Validation error updating change request {changerequest_number}: {error_msg}")
            else:
                logger.error(f"Error updating change request {changerequest_number}: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format success response
        if result.get("success"):
            updated_changerequest = result.get("updated_changerequest", {})
            message = result.get("message", f"Change request {changerequest_number} updated successfully")
            
            # Format the updated change request data for display
            if updated_changerequest:
                formatted_result = format_change_request_display(updated_changerequest)
                response = f"{message}\n\nUpdated Change Request Details:\n{formatted_result}"
            else:
                response = message
            
            logger.info(f"Successfully updated change request: {changerequest_number}")
            return response
        else:
            return f"Error: Update failed for change request {changerequest_number}"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error updating change request {changerequest_number}: {e}")
        return f"Error: {error_msg}"


@server.tool
@require_scope(auth_config.change_request_write_scope)
async def approve_change_request(
    changerequest_number: str,
    state: str,
    approver_email: str,
    approver_name: str = None,
    on_behalf: str = None
) -> str:
    """Approve or reject a change request by change request number.
    
    Allows authorized users to approve or reject a change request that is in Authorize state.
    The approval decision (approved/rejected) along with approver details are recorded.
    
    Args:
        changerequest_number: The change request number to approve/reject (e.g., CHG0035060)
        state: Either 'approved' or 'rejected' - the approval decision
        approver_email: Email id of the approver user (e.g., john.doe@company.com)
        approver_name: User name who approved/rejected the CR (e.g., "John Doe")
        on_behalf: API service account used for approving CR (e.g., "svc_api_account")
        
    Returns:
        Success message with approval details or error message
        
    Note:
        - Change request must be in Authorize state (state=3) to be approved/rejected
        - Only valid approval users can perform this action
        - The approval is recorded with timestamp and approver details
    """
    logger.info(f"Processing {state} for change request: {changerequest_number}")
    
    try:
        tools = await get_change_request_tools()
        
        result = await tools.approve_change_request(
            changerequest_number=changerequest_number,
            state=state,
            approver_email=approver_email,
            approver_name=approver_name,
            on_behalf=on_behalf
        )
        
        # Check for errors in the response
        if "error" in result:
            error_msg = result["error"]
            error_type = result.get("error_type", "unknown")
            
            if error_type == "not_found":
                logger.warning(f"Change request {changerequest_number} not found for approval")
            elif error_type == "validation_error":
                logger.warning(f"Validation error approving change request {changerequest_number}: {error_msg}")
            else:
                logger.error(f"Error approving change request {changerequest_number}: {error_msg}")
            
            return f"Error: {error_msg}"
        
        # Format success response
        if result.get("success"):
            approval_state = result.get("approval_state", state)
            approver = result.get("approver_email", approver_email)
            message = result.get("message", f"Change request {changerequest_number} has been {approval_state}")
            
            response = f"{message}\n\n"
            response += "=" * 60 + "\n"
            response += f"Change Request: {changerequest_number}\n"
            response += f"Approval State: {approval_state.upper()}\n"
            response += f"Approved By: {approver}\n"
            if approver_name:
                response += f"Approver Name: {approver_name}\n"
            if on_behalf:
                response += f"On Behalf Of: {on_behalf}\n"
            response += "=" * 60
            
            logger.info(f"Successfully {approval_state} change request: {changerequest_number}")
            return response
        else:
            return f"Error: Approval failed for change request {changerequest_number}"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error processing approval for change request {changerequest_number}: {e}")
        return f"Error: {error_msg}"


@server.tool
@require_scope(auth_config.incident_task_read_scope)
async def get_incident_task(incident_task_number: str) -> str:
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
        tools = await get_incident_task_tools()
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


@server.tool
@require_scope(auth_config.incident_task_read_scope)
async def list_incident_task_fields() -> str:
    """List all available incident task fields and their descriptions.
    
    Returns:
        Formatted list of incident task fields with descriptions and examples
    """
    return get_incident_task_fields_info()


@server.tool
@require_scope(auth_config.incident_task_write_scope)
async def update_incident_task(
    incident_task_number: str,
    short_description: str,
    state: int,
    description: str = None,
    priority: int = None,
    assignment_group: str = None,
    assigned_to: str = None
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
        tools = await get_incident_task_tools()
        
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


@server.tool
@require_scope(auth_config.incident_task_write_scope)
async def create_incident_task(
    incident_number: str,
    short_description: str,
    service_name: str,
    company_name: str,
    configuration_item: str,
    description: str = None,
    priority: int = None,
    assignment_group: str = None,
    assigned_to: str = None
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
    logger.info("Creating new incident task")
    
    try:
        tools = await get_incident_task_tools()
        
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


def main():
    """Main entry point for FastMCP ServiceNow server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ServiceNow FastMCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "http", "sse"], 
        default="stdio",
        help="Transport protocol to use"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host address for HTTP/SSE")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE")
    parser.add_argument("--no-banner", action="store_true", help="Disable startup banner")
    
    args = parser.parse_args()
    
    try:
        server.run(
            transport=args.transport,
            host=args.host,
            port=args.port,
            show_banner=not args.no_banner
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()