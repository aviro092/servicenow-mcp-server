"""Simplified MCP tool handlers for change request management."""

import logging
from typing import Optional

from auth.decorators import requires_scope
from config import get_auth_config
from container import get_container
from tools.change_request_tools import format_change_request_display, get_change_request_fields_info

logger = logging.getLogger(__name__)
auth_config = get_auth_config()


@requires_scope(auth_config.change_request_read_scope)
async def search_change_requests(
    active: bool = True,
    requested_by: Optional[str] = None,
    agreement_id: Optional[str] = None,
    company: Optional[str] = None,
    category: Optional[str] = None,
    cmdb_ci: Optional[str] = None,
    type: Optional[str] = None,
    priority: Optional[int] = None,
    risk: Optional[int] = None,
    impact: Optional[int] = None,
    state: Optional[int] = None,
    assignment_group: Optional[str] = None,
    assigned_to: Optional[str] = None
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
        container = get_container()
        tools = await container.get_change_request_tools()
        
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
        
        # Debug logging to understand the result type and content
        logger.debug(f"Search result type: {type(result)}")
        logger.debug(f"Search result content: {result}")
        
        # Handle case where result is not a dictionary
        if not isinstance(result, dict):
            logger.error(f"Expected dict result but got {type(result)}: {result}")
            return f"Error: Unexpected result format from search_change_requests. Expected dict but got {type(result)}"
        
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



@requires_scope(auth_config.change_request_read_scope)
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
        container = get_container()
        tools = await container.get_change_request_tools()
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



@requires_scope(auth_config.change_request_read_scope)
async def list_change_request_fields() -> str:
    """List all available change request fields and their descriptions.
    
    Returns:
        Formatted list of change request fields with descriptions and examples
    """
    return get_change_request_fields_info()



@requires_scope(auth_config.change_request_write_scope)
async def update_change_request(
    changerequest_number: str,
    company_name: str,
    description: Optional[str] = None,
    comments: Optional[str] = None,
    on_hold: Optional[bool] = None,
    on_hold_reason: Optional[str] = None,
    resolved: Optional[bool] = None,
    customer_reference_id: Optional[str] = None
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
        container = get_container()
        tools = await container.get_change_request_tools()
        
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
        
        # Handle case where result is not a dictionary
        if not isinstance(result, dict):
            logger.error(f"Expected dict result but got {type(result)}: {result}")
            return f"Error: Unexpected result format from update_change_request. Expected dict but got {type(result)}"
        
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



@requires_scope(auth_config.change_request_write_scope)
async def approve_change_request(
    changerequest_number: str,
    state: str,
    approver_email: str,
    approver_name: Optional[str] = None,
    on_behalf: Optional[str] = None
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
        container = get_container()
        tools = await container.get_change_request_tools()
        
        result = await tools.approve_change_request(
            changerequest_number=changerequest_number,
            state=state,
            approver_email=approver_email,
            approver_name=approver_name,
            on_behalf=on_behalf
        )
        
        # Handle case where result is not a dictionary
        if not isinstance(result, dict):
            logger.error(f"Expected dict result but got {type(result)}: {result}")
            return f"Error: Unexpected result format from approve_change_request. Expected dict but got {type(result)}"
        
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