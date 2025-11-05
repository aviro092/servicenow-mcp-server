"""Change request management tools for ServiceNow MCP Server."""

import logging
from typing import Dict, Any, Optional
from api.client import ServiceNowClient
from models.change_request import ChangeRequestSearchRequest, ChangeRequestResponse, ChangeRequestUpdateRequest

logger = logging.getLogger(__name__)


class ChangeRequestTools:
    """Tools for managing ServiceNow change requests."""
    
    def __init__(self, client: ServiceNowClient):
        """Initialize change request tools.
        
        Args:
            client: ServiceNow API client instance
        """
        self.client = client
    
    async def search_change_requests(
        self,
        active: Optional[bool] = True,
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
    ) -> Dict[str, Any]:
        """Search change request records based on criteria.
        
        Args:
            active: Select active records (default True)
            requested_by: Search by Change Request's Requestor name
            agreement_id: Search by Change Request's Agreement Id
            company: Search by Change Request's Company
            category: Search by Change Request's Category
            cmdb_ci: Search by Change Request's CMDB CI
            type: Search by Change Request's type
            priority: Search by Change Request's priority (1=Critical, 2=High, 3=Medium, 4=Low)
            risk: Search by Change Request's risk (1-5)
            impact: Search by Change Request's impact (1=Critical, 2=High, 3=Medium, 4=Low)
            state: Search by Change Request's state (1-8)
            assignment_group: Search by Assignment Group
            assigned_to: Search by Assigned user details
            
        Returns:
            Dictionary containing search results or error information
        """
        try:
            # Validate input parameters
            search_request = ChangeRequestSearchRequest(
                active=active,
                requested_by=requested_by,
                agreement_id=agreement_id,
                company=company,
                category=category,
                cmdb_ci=cmdb_ci,
                type=type,
                priority=priority,
                risk=risk,
                impact=impact,
                state=state,
                assignment_group=assignment_group,
                assigned_to=assigned_to
            )
            
            # Convert to dict, filtering out None values
            search_params = {
                k: v for k, v in search_request.model_dump().items() if v is not None
            }
            
            logger.info(f"Searching change requests with criteria: {search_params}")
            
            # Perform the search
            result = await self.client.search_change_requests(search_params)
            
            if result.get("success"):
                logger.info(f"Successfully found {result.get('count', 0)} change requests")
                return {
                    "success": True,
                    "count": result.get("count", 0),
                    "change_requests": result.get("change_requests", []),
                    "search_criteria": search_params,
                    "message": f"Found {result.get('count', 0)} change request(s)"
                }
            else:
                error_msg = result.get("error", "Unknown error occurred during search")
                logger.warning(f"Change request search failed: {error_msg}")
                return {
                    "error": error_msg,
                    "error_type": "search_error",
                    "search_criteria": search_params
                }
                
        except ValueError as e:
            error_msg = f"Invalid search parameters: {str(e)}"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "error_type": "validation_error"
            }
        except Exception as e:
            error_msg = f"Unexpected error during change request search: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "error_type": "unexpected_error"
            }

    async def get_change_request(self, changerequest_number: str) -> Dict[str, Any]:
        """Get change request details by change request number.
        
        Args:
            changerequest_number: The change request number (e.g., CHG0035060)
            
        Returns:
            Dictionary containing change request details or error information
        """
        try:
            logger.info(f"Fetching change request details for: {changerequest_number}")
            
            # Validate change request number format (basic validation)
            if not changerequest_number or not isinstance(changerequest_number, str):
                error_msg = "Change request number is required and must be a string"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "error_type": "validation_error"
                }
            
            # Clean up the change request number
            changerequest_number = changerequest_number.strip()
            
            # Get change request from ServiceNow API
            changerequest_data = await self.client.get_change_request(changerequest_number)
            
            logger.info(f"Successfully retrieved change request: {changerequest_number}")
            
            return {
                "success": True,
                "changerequest": changerequest_data,
                "changerequest_number": changerequest_number
            }
            
        except Exception as e:
            from api.exceptions import ServiceNowNotFoundError
            
            if isinstance(e, ServiceNowNotFoundError):
                error_msg = f"Change request '{changerequest_number}' not found"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "error_type": "not_found"
                }
            else:
                error_msg = f"Unexpected error retrieving change request: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    "error": error_msg,
                    "error_type": "unexpected_error"
                }

    async def update_change_request(
        self,
        changerequest_number: str,
        company_name: str,
        description: Optional[str] = None,
        comments: Optional[str] = None,
        on_hold: Optional[bool] = None,
        on_hold_reason: Optional[str] = None,
        resolved: Optional[bool] = None,
        customer_reference_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update change request by change request number.
        
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
            Dictionary containing update results or error information
        """
        try:
            logger.info(f"Updating change request: {changerequest_number}")
            
            # Validate input parameters
            update_request = ChangeRequestUpdateRequest(
                company_name=company_name,
                description=description,
                comments=comments,
                on_hold=on_hold,
                on_hold_reason=on_hold_reason,
                resolved=resolved,
                customer_reference_id=customer_reference_id
            )
            
            # Convert to dict, filtering out None values
            update_params = {
                k: v for k, v in update_request.model_dump().items() if v is not None
            }
            
            if not update_params:
                error_msg = "No update fields provided. At least company_name must be specified for update."
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "error_type": "validation_error"
                }
            
            logger.debug(f"Update parameters: {update_params}")
            
            # Perform the update
            updated_data = await self.client.update_change_request(changerequest_number, update_params)
            
            logger.info(f"Successfully updated change request: {changerequest_number}")
            
            return {
                "success": True,
                "updated_changerequest": updated_data,
                "changerequest_number": changerequest_number,
                "message": f"Change request {changerequest_number} updated successfully"
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
                error_msg = f"Change request '{changerequest_number}' not found"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "error_type": "not_found"
                }
            else:
                error_msg = f"Unexpected error updating change request: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    "error": error_msg,
                    "error_type": "unexpected_error"
                }

    async def approve_change_request(
        self,
        changerequest_number: str,
        state: str,
        approver_email: str,
        approver_name: Optional[str] = None,
        on_behalf: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve or reject a change request.
        
        Args:
            changerequest_number: The change request number to approve/reject (e.g., CHG0035060)
            state: Either 'approved' or 'rejected'
            approver_email: Email id of the approver user
            approver_name: User name who approved/rejected the CR
            on_behalf: API service account used for approving CR
            
        Returns:
            Dictionary containing approval results or error information
        """
        try:
            logger.info(f"Processing {state} for change request: {changerequest_number}")
            
            # Import models here to avoid circular imports
            from models import ChangeRequestApprovalRequest
            
            # Validate input parameters
            approval_request = ChangeRequestApprovalRequest(
                state=state,
                approver_email=approver_email,
                approver_name=approver_name,
                on_behalf=on_behalf
            )
            
            # Build approval data dictionary
            approval_data = approval_request.model_dump(exclude_none=True)
            
            # Call the API client to approve/reject the change request
            response = await self.client.approve_change_request(
                changerequest_number,
                approval_data
            )
            
            # Check if response indicates success
            if response and not isinstance(response, dict):
                response = {"result": response}
            
            result = response.get("result", response)
            
            logger.info(f"Successfully {state} change request: {changerequest_number}")
            
            return {
                "success": True,
                "changerequest_number": changerequest_number,
                "approval_state": state,
                "approver_email": approver_email,
                "message": f"Change request {changerequest_number} has been {state} by {approver_email}"
            }
            
        except ValueError as e:
            error_msg = f"Invalid approval parameters: {str(e)}"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "error_type": "validation_error"
            }
        except Exception as e:
            from api.exceptions import ServiceNowNotFoundError
            
            if isinstance(e, ServiceNowNotFoundError):
                error_msg = f"Change request '{changerequest_number}' not found"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "error_type": "not_found"
                }
            else:
                error_msg = f"Unexpected error processing approval: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return {
                    "error": error_msg,
                    "error_type": "unexpected_error"
                }


def format_change_request_display(change_request: Dict[str, Any]) -> str:
    """Format a change request for display.
    
    Args:
        change_request: Change request data from ServiceNow API
        
    Returns:
        Formatted string representation of the change request
    """
    lines = []
    
    # Header
    number = change_request.get("number", "Unknown")
    lines.append(f"Change Request: {number}")
    lines.append("=" * 60)
    
    # Basic Information
    lines.append("\n📋 BASIC INFORMATION")
    lines.append("-" * 30)
    lines.append(f"Number: {change_request.get('number', 'N/A')}")
    lines.append(f"State: {_format_change_state(change_request.get('state'))}")
    lines.append(f"Type: {change_request.get('type', 'N/A')}")
    lines.append(f"Category: {change_request.get('category', 'N/A')}")
    lines.append(f"Priority: {_format_priority(change_request.get('priority'))}")
    lines.append(f"Risk: {_format_risk(change_request.get('risk'))}")
    lines.append(f"Impact: {_format_impact(change_request.get('impact'))}")
    
    # Request Information
    lines.append("\n👤 REQUEST INFORMATION")
    lines.append("-" * 30)
    lines.append(f"Requested By: {change_request.get('requested_by', 'N/A')}")
    lines.append(f"Company: {change_request.get('company', 'N/A')}")
    lines.append(f"Agreement ID: {change_request.get('agreement_id', 'N/A')}")
    
    # Assignment Information
    lines.append("\n👥 ASSIGNMENT")
    lines.append("-" * 30)
    lines.append(f"Assignment Group: {change_request.get('assignment_group', 'N/A')}")
    lines.append(f"Assigned To: {change_request.get('assigned_to', 'N/A')}")
    
    # Description
    if change_request.get("short_description"):
        lines.append("\n📄 DESCRIPTION")
        lines.append("-" * 30)
        lines.append(f"Short Description: {change_request.get('short_description')}")
        
        if change_request.get("description"):
            lines.append(f"Full Description: {change_request.get('description')}")
    
    # Dates
    lines.append("\n📅 DATES")
    lines.append("-" * 30)
    lines.append(f"Created On: {_format_date(change_request.get('created_on'))}")
    lines.append(f"Start Date: {_format_date(change_request.get('start_date'))}")
    lines.append(f"End Date: {_format_date(change_request.get('end_date'))}")
    lines.append(f"Updated On: {_format_date(change_request.get('updated_on'))}")
    
    if change_request.get("closed_at"):
        lines.append(f"Closed At: {_format_date(change_request.get('closed_at'))}")
    
    # Technical Information
    if change_request.get("cmdb_ci"):
        lines.append("\n🔧 TECHNICAL INFORMATION")
        lines.append("-" * 30)
        lines.append(f"CMDB CI: {change_request.get('cmdb_ci')}")
    
    # Plans and Documentation
    plans = []
    if change_request.get("implementation_plan"):
        plans.append(f"Implementation Plan: {change_request.get('implementation_plan')}")
    if change_request.get("test_plan"):
        plans.append(f"Test Plan: {change_request.get('test_plan')}")
    if change_request.get("backout_plan"):
        plans.append(f"Backout Plan: {change_request.get('backout_plan')}")
    
    if plans:
        lines.append("\n📋 PLANS")
        lines.append("-" * 30)
        lines.extend(plans)
    
    # Work Notes and Comments
    if change_request.get("work_notes") or change_request.get("comments"):
        lines.append("\n💬 NOTES & COMMENTS")
        lines.append("-" * 30)
        if change_request.get("work_notes"):
            lines.append(f"Work Notes: {change_request.get('work_notes')}")
        if change_request.get("comments"):
            lines.append(f"Comments: {change_request.get('comments')}")
    
    # Additional Information
    additional_info = []
    if change_request.get("phase"):
        additional_info.append(f"Phase: {change_request.get('phase')}")
    if change_request.get("phase_state"):
        additional_info.append(f"Phase State: {change_request.get('phase_state')}")
    if change_request.get("approval"):
        additional_info.append(f"Approval: {change_request.get('approval')}")
    if change_request.get("reason"):
        additional_info.append(f"Reason: {change_request.get('reason')}")
    
    if additional_info:
        lines.append("\n🔍 ADDITIONAL INFORMATION")
        lines.append("-" * 30)
        lines.extend(additional_info)
    
    return "\n".join(lines)


def _format_change_state(state: Any) -> str:
    """Format change request state for display."""
    if state is None:
        return "N/A"
    
    state_map = {
        1: "New",
        2: "Assess",
        3: "Authorize",
        4: "Scheduled",
        5: "Implement",
        6: "Review",
        7: "Closed",
        8: "Canceled"
    }
    
    state_int = int(state) if str(state).isdigit() else None
    return state_map.get(state_int, f"Unknown ({state})")


def _format_priority(priority: Any) -> str:
    """Format priority for display."""
    if priority is None:
        return "N/A"
    
    priority_map = {
        1: "Critical",
        2: "High", 
        3: "Medium",
        4: "Low"
    }
    
    priority_int = int(priority) if str(priority).isdigit() else None
    return priority_map.get(priority_int, f"Unknown ({priority})")


def _format_risk(risk: Any) -> str:
    """Format risk for display."""
    if risk is None:
        return "N/A"
    
    risk_map = {
        1: "Very Low",
        2: "Low",
        3: "Medium", 
        4: "High",
        5: "Very High"
    }
    
    risk_int = int(risk) if str(risk).isdigit() else None
    return risk_map.get(risk_int, f"Unknown ({risk})")


def _format_impact(impact: Any) -> str:
    """Format impact for display."""
    if impact is None:
        return "N/A"
    
    impact_map = {
        1: "Critical",
        2: "High",
        3: "Medium", 
        4: "Low"
    }
    
    impact_int = int(impact) if str(impact).isdigit() else None
    return impact_map.get(impact_int, f"Unknown ({impact})")


def _format_date(date_str: Any) -> str:
    """Format date string for display."""
    if not date_str:
        return "N/A"
    
    # Handle different date formats that might come from ServiceNow
    try:
        if isinstance(date_str, str):
            # Remove timezone info and microseconds for cleaner display
            if "T" in date_str:
                date_part = date_str.split("T")[0]
                time_part = date_str.split("T")[1].split(".")[0] if "." in date_str else date_str.split("T")[1]
                return f"{date_part} {time_part}"
            else:
                return date_str
        else:
            return str(date_str)
    except Exception:
        return str(date_str)


def get_change_request_fields_info() -> str:
    """Get information about available change request fields.
    
    Returns:
        Formatted string with field descriptions and examples
    """
    lines = []
    lines.append("ServiceNow Change Request Fields")
    lines.append("=" * 60)
    
    fields = [
        ("number", "Change request number", "CHG0000001"),
        ("state", "Change request state (1=New, 2=Assess, 3=Authorize, 4=Scheduled, 5=Implement, 6=Review, 7=Closed, 8=Canceled)", "1"),
        ("type", "Change request type", "Standard, Emergency, Normal"),
        ("category", "Category", "Hardware, Software, Network"),
        ("priority", "Priority (1=Critical, 2=High, 3=Medium, 4=Low)", "2"),
        ("risk", "Risk level (1=Very Low, 2=Low, 3=Medium, 4=High, 5=Very High)", "3"),
        ("impact", "Impact (1=Critical, 2=High, 3=Medium, 4=Low)", "2"),
        ("requested_by", "Person who requested the change", "user@company.com"),
        ("company", "Company associated with the change", "ACME Corp"),
        ("assignment_group", "Group assigned to handle the change", "Change Management"),
        ("assigned_to", "Individual assigned to the change", "John Doe"),
        ("short_description", "Brief description of the change", "Update server configuration"),
        ("description", "Detailed description of the change", "Full details..."),
        ("cmdb_ci", "Configuration item affected", "Server001"),
        ("agreement_id", "Service agreement identifier", "SLA001"),
        ("start_date", "Planned start date", "2023-12-01 09:00:00"),
        ("end_date", "Planned end date", "2023-12-01 17:00:00"),
        ("implementation_plan", "How the change will be implemented", "Step by step plan..."),
        ("test_plan", "How the change will be tested", "Testing procedures..."),
        ("backout_plan", "How to reverse the change if needed", "Rollback procedures..."),
        ("work_notes", "Internal work notes", "Progress updates..."),
        ("comments", "Comments and communication", "Additional information..."),
        ("phase", "Current phase of the change", "Planning, Implementation"),
        ("approval", "Approval status", "Approved, Pending, Rejected"),
        ("reason", "Reason for the change", "Performance improvement"),
    ]
    
    for field, description, example in fields:
        lines.append(f"\n{field}:")
        lines.append(f"  Description: {description}")
        lines.append(f"  Example: {example}")
    
    lines.append("\n" + "=" * 60)
    lines.append("Search Parameters:")
    lines.append("All fields above can be used as search criteria.")
    lines.append("Multiple criteria can be combined for more specific searches.")
    
    return "\n".join(lines)