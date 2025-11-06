"""Incident-related MCP tools."""

from typing import Any, Dict, Optional

import logging
from api import ServiceNowClient, ServiceNowAPIError, ServiceNowNotFoundError
from models.incident import IncidentResponse, IncidentUpdateRequest, IncidentCreateRequest, IncidentSearchRequest

logger = logging.getLogger(__name__)


def format_incident_display(incident: Dict[str, Any]) -> str:
    """Format incident data for human-readable display.
    
    Args:
        incident: Incident data dictionary
        
    Returns:
        Formatted string representation
    """
    lines = ["Incident Details:"]
    lines.append("=" * 60)
    
    # Basic information section
    basic_fields = [
        ("Number", "number"),
        ("State", "state"),
        ("Priority", "priority"),
        ("Impact", "impact"),
        ("Urgency", "urgency"),
        ("Short Description", "short_description"),
    ]
    
    lines.append("\nBasic Information:")
    lines.append("-" * 20)
    for label, field in basic_fields:
        value = incident.get(field, "N/A")
        if value and value != "N/A":
            lines.append(f"{label}: {value}")
    
    # Contact information section
    contact_fields = [
        ("Requested By", "requested_by"),
        ("Company", "company"),
        ("Service", "service_name"),
        ("Category", "category"),
        ("Subcategory", "subcategory"),
    ]
    
    lines.append("\nContact & Classification:")
    lines.append("-" * 28)
    for label, field in contact_fields:
        value = incident.get(field, "N/A")
        if value and value != "N/A":
            lines.append(f"{label}: {value}")
    
    # Assignment information
    assignment_fields = [
        ("Assignment Group", "assignment_group"),
        ("Assigned To", "assigned_to"),
        ("Configuration Item", "configuration_item"),
    ]
    
    lines.append("\nAssignment:")
    lines.append("-" * 11)
    for label, field in assignment_fields:
        value = incident.get(field, "N/A")
        if value and value != "N/A":
            lines.append(f"{label}: {value}")
    
    # Timestamps
    time_fields = [
        ("Created Date", "created_date"),
        ("Created By", "created_by"),
        ("Modified Date", "modified_date"),
        ("Modified By", "modified_by"),
        ("Closed Date", "closed_date"),
        ("Closed By", "closed_by"),
    ]
    
    lines.append("\nTimestamps:")
    lines.append("-" * 11)
    for label, field in time_fields:
        value = incident.get(field)
        if value:
            lines.append(f"{label}: {value}")
    
    # Description
    if incident.get("description"):
        lines.append(f"\nDescription:")
        lines.append("-" * 12)
        lines.append(incident["description"])
    
    # Resolution information
    resolution_info = incident.get("resolution_info")
    if resolution_info:
        lines.append(f"\nResolution:")
        lines.append("-" * 11)
        if resolution_info.get("resolution_code"):
            lines.append(f"Code: {resolution_info['resolution_code']}")
        if resolution_info.get("resolved_at"):
            lines.append(f"Resolved At: {resolution_info['resolved_at']}")
        if resolution_info.get("resolved_by"):
            lines.append(f"Resolved By: {resolution_info['resolved_by']}")
        if resolution_info.get("resolution_notes"):
            lines.append(f"Notes: {resolution_info['resolution_notes']}")
        if resolution_info.get("knowledge"):
            lines.append(f"Knowledge Article: {resolution_info['knowledge']}")
    
    # Incident tasks
    tasks = incident.get("incident_tasks", [])
    if tasks:
        lines.append(f"\nIncident Tasks ({len(tasks)}):")
        lines.append("-" * 20)
        for i, task in enumerate(tasks, 1):
            lines.append(f"{i}. {task.get('task_number', 'N/A')}")
            lines.append(f"   Description: {task.get('short_description', 'N/A')}")
            lines.append(f"   State: {task.get('state', 'N/A')}")
            lines.append(f"   Assigned to: {task.get('assigned_to', 'Unassigned')}")
            if task.get('assignment_group'):
                lines.append(f"   Assignment Group: {task['assignment_group']}")
            if i < len(tasks):
                lines.append("")
    
    # Notes and comments
    if incident.get("notes"):
        lines.append(f"\nLatest Notes:")
        lines.append("-" * 13)
        lines.append(incident["notes"])
    
    if incident.get("comments"):
        lines.append(f"\nLatest Comments:")
        lines.append("-" * 16)
        lines.append(incident["comments"])
    
    # Customer reference
    if incident.get("customer_reference_id"):
        lines.append(f"\nCustomer Reference: {incident['customer_reference_id']}")
    
    return "\n".join(lines)


def get_incident_fields_info() -> str:
    """Get formatted list of all available incident fields and their descriptions.
    
    Returns:
        Formatted string with incident field descriptions
    """
    fields_info = [
        ("number", "CMSP ServiceNow ticket number", "INC654321"),
        ("requested_by", "Creator of the ServiceNow ticket", "John Doe"),
        ("company", "Account mapped in CMSP ServiceNow", "Snow World"),
        ("service_name", "Service name mapped to cmdb_ci_service table", "test SNSR"),
        ("category", "Category details from sys_choice table", "Performance"),
        ("subcategory", "Incident Sub-Category details", "Timeout"),
        ("configuration_item", "Configuration item sys_id", "000297901469B"),
        ("source", "Incident creation source", "self-service"),
        ("state", "Incident current state", "In Progress"),
        ("impact", "Incident impact value", "3 - Medium"),
        ("urgency", "Incident urgency value", "2 - High"),
        ("priority", "Incident priority value", "3 - Medium"),
        ("assignment_group", "Assignment Group", "NGCS-ADSS-Support-Engineer"),
        ("assigned_to", "Assigned user", "John Doe"),
        ("short_description", "Incident short description (max 120 chars)", "Brief issue summary"),
        ("description", "Incident description (max 4000 chars)", "Detailed issue description"),
        ("comments", "Last updated comments", "Latest comment details"),
        ("notes", "Last updated notes", "Latest note details"),
        ("created_by", "Created user email", "john.doe@company.com"),
        ("created_date", "Incident created date", "2022-01-06 07:10:04"),
        ("modified_by", "Last modified user", "jane.smith@company.com"),
        ("modified_date", "Last modified date", "2022-02-09 09:07:24"),
        ("closed_by", "Incident closed user (if closed)", "admin@company.com"),
        ("closed_date", "Incident closed date (if closed)", "2022-02-10 15:30:00"),
        ("customer_reference_id", "Customer Incident ticket ID", "INC9054378"),
    ]
    
    lines = ["ServiceNow Incident Fields:"]
    lines.append("=" * 40)
    lines.append("")
    
    for field, description, example in fields_info:
        lines.append(f"Field: {field}")
        lines.append(f"Description: {description}")
        lines.append(f"Example: {example}")
        lines.append("")
    
    # Resolution info fields
    lines.append("Resolution Information Fields:")
    lines.append("-" * 30)
    resolution_fields = [
        ("resolution_code", "Incident closed code", "Integer"),
        ("resolution_notes", "Incident resolution notes", "Text"),
        ("resolved_at", "Incident resolved date", "2022-02-10 14:30:00"),
        ("resolved_by", "User who resolved the incident", "resolver@company.com"),
        ("knowledge", "Mapped knowledge article info", "URL"),
    ]
    
    for field, description, example in resolution_fields:
        lines.append(f"Field: {field}")
        lines.append(f"Description: {description}")
        lines.append(f"Example: {example}")
        lines.append("")
    
    # Task fields
    lines.append("Incident Task Fields:")
    lines.append("-" * 20)
    task_fields = [
        ("task_number", "CMSP ServiceNow Incident task number", "TASK0131780"),
        ("state", "Incident task current state", "Open"),
        ("short_description", "Task short description (max 120 chars)", "Task summary"),
        ("configuration_item", "Configuration item sys_id", "000297901469B"),
        ("business_service", "Service name", "test SNSR"),
        ("assignment_group", "Assignment Group sys_id", "NGCS-ADSS-Support-Engineer"),
        ("assigned_to", "Assigned user", "John Doe"),
    ]
    
    for field, description, example in task_fields:
        lines.append(f"Field: {field}")
        lines.append(f"Description: {description}")
        lines.append(f"Example: {example}")
        lines.append("")
    
    return "\n".join(lines)


class IncidentTools:
    """Collection of incident-related tools for MCP server."""
    
    def __init__(self, client: ServiceNowClient):
        """Initialize incident tools.
        
        Args:
            client: ServiceNow API client instance
        """
        self.client = client
    
    async def get_incident(self, incident_number: str) -> Dict[str, Any]:
        """Get incident record details by incident number.
        
        This tool retrieves comprehensive details about a ServiceNow incident,
        including its status, assignment, description, and associated tasks.
        
        Args:
            incident_number: The incident number (e.g., INC654321)
            
        Returns:
            Dictionary containing:
                - number: Incident number
                - requested_by: Creator of the incident
                - company: Company/account name
                - service_name: Associated service
                - category: Incident category
                - subcategory: Incident subcategory
                - state: Current state
                - priority: Priority level
                - assignment_group: Assigned group
                - assigned_to: Assigned individual
                - short_description: Brief description
                - description: Full description
                - created_date: Creation timestamp
                - modified_date: Last modification timestamp
                - incident_tasks: List of associated tasks
                - And other incident fields
                
        Raises:
            ServiceNowNotFoundError: If incident not found
            ServiceNowAPIError: For other API errors
        """
        try:
            logger.debug(f"Fetching incident details for: {incident_number}")
            incident_data = await self.client.get_incident(incident_number)
            
            # Validate with Pydantic model if needed
            try:
                incident = IncidentResponse(**incident_data)
                logger.debug(f"Successfully validated incident data for: {incident_number}")
                return incident.model_dump()
            except Exception as e:
                logger.warning(f"Data validation failed for incident {incident_number}: {e}")
                # Return raw data if validation fails
                return incident_data
                
        except ServiceNowNotFoundError:
            logger.warning(f"Incident not found: {incident_number}")
            return {
                "error": f"Incident {incident_number} not found",
                "error_type": "not_found"
            }
        except ServiceNowAPIError as e:
            logger.error(f"API error fetching incident {incident_number}: {e}")
            return {
                "error": str(e),
                "error_type": "api_error",
                "status_code": getattr(e, "status_code", None)
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching incident {incident_number}: {e}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown"
            }
    
    async def update_incident(self, incident_number: str, **kwargs) -> Dict[str, Any]:
        """Update incident record by incident number.
        
        This tool updates an existing ServiceNow incident with new values.
        All fields are optional except incident_number.
        
        Args:
            incident_number: The incident number to update (e.g., INC654321)
            **kwargs: Update fields including:
                - state: Incident state (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)
                - impact: Impact level (1=Critical, 2=High, 3=Medium, 4=Low)
                - urgency: Urgency level (1=Critical, 2=High, 3=Medium, 4=Low)
                - category: Category (e.g., "Performance")
                - subcategory: Subcategory (e.g., "Slow Response")
                - short_description: Brief description (max 120 chars)
                - description: Full description (max 4000 chars)
                - holdreason: Reason for hold state
                - service_impacting: Service impact details
                - comments: Add comments to incident
                - notes: Add notes to incident
                - customer_reference_id: Customer ticket ID
                - resolution_info: Resolution details (dict with resolution_code, resolution_notes, etc.)
                
        Returns:
            Dictionary containing:
                - success: True if update successful
                - updated_incident: Updated incident data
                - message: Success message
                Or error information if failed
                
        Raises:
            ServiceNowNotFoundError: If incident not found
            ServiceNowAPIError: For other API errors
        """
        try:
            logger.debug(f"Updating incident: {incident_number}")
            
            # Create update request data, filtering out None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            
            if not update_data:
                return {
                    "error": "No update fields provided",
                    "error_type": "validation_error"
                }
            
            # Add the incident number to the update data
            update_data["number"] = incident_number
            
            # Validate update data with Pydantic model
            try:
                update_request = IncidentUpdateRequest(**update_data)
                validated_data = update_request.model_dump(exclude_none=True)
                logger.debug(f"Validated update data for incident {incident_number}")
            except Exception as e:
                logger.warning(f"Update data validation failed for incident {incident_number}: {e}")
                return {
                    "error": f"Invalid update data: {str(e)}",
                    "error_type": "validation_error"
                }
            
            # Remove incident number from the data sent to API (it's in the URL)
            api_data = {k: v for k, v in validated_data.items() if k != "number"}
            
            # Make the API call
            updated_data = await self.client.update_incident(incident_number, api_data)
            
            logger.info(f"Successfully updated incident: {incident_number}")
            return {
                "success": True,
                "updated_incident": updated_data,
                "message": f"Incident {incident_number} updated successfully"
            }
                
        except ServiceNowNotFoundError:
            logger.warning(f"Incident not found for update: {incident_number}")
            return {
                "error": f"Incident {incident_number} not found",
                "error_type": "not_found"
            }
        except ServiceNowAPIError as e:
            logger.error(f"API error updating incident {incident_number}: {e}")
            return {
                "error": str(e),
                "error_type": "api_error",
                "status_code": getattr(e, "status_code", None)
            }
        except Exception as e:
            logger.error(f"Unexpected error updating incident {incident_number}: {e}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown"
            }
    
    async def create_incident(
        self,
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
    ) -> Dict[str, Any]:
        """Create a new incident record.
        
        This tool creates a new ServiceNow incident with the provided details.
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
            Dictionary containing:
                - success: True if creation successful
                - created_incident: Created incident data with incident number
                - message: Success message
                Or error information if failed
                
        Raises:
            ServiceNowAPIError: For API errors
        """
        try:
            logger.debug("Creating new incident")
            
            # Build create request data
            create_data = {
                "short_description": short_description,
                "description": description,
                "service_name": service_name,
                "urgency": urgency,
            }
            
            # Add optional fields if provided
            optional_fields = {
                "impact": impact,
                "category": category,
                "subcategory": subcategory,
                "configuration_item": configuration_item,
                "assigned_to": assigned_to,
                "assignment_group": assignment_group,
                "contact_type": contact_type,
                "customer_reference_id": customer_reference_id,
            }
            
            for key, value in optional_fields.items():
                if value is not None:
                    create_data[key] = value
            
            # Validate create data with Pydantic model
            try:
                create_request = IncidentCreateRequest(**create_data)
                validated_data = create_request.model_dump(exclude_none=True)
                logger.debug("Validated create data for new incident")
            except Exception as e:
                logger.warning(f"Create data validation failed: {e}")
                return {
                    "error": f"Invalid create data: {str(e)}",
                    "error_type": "validation_error"
                }
            
            # Make the API call
            created_data = await self.client.create_incident(validated_data)
            
            # Extract incident number from response
            incident_number = created_data.get("number", "Unknown")
            logger.info(f"Successfully created incident: {incident_number}")
            
            return {
                "success": True,
                "created_incident": created_data,
                "incident_number": incident_number,
                "message": f"Incident {incident_number} created successfully"
            }
                
        except ServiceNowAPIError as e:
            logger.error(f"API error creating incident: {e}")
            return {
                "error": str(e),
                "error_type": "api_error",
                "status_code": getattr(e, "status_code", None)
            }
        except Exception as e:
            logger.error(f"Unexpected error creating incident: {e}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown"
            }
    
    async def search_incidents(self, **kwargs) -> Dict[str, Any]:
        """Search incident records based on query parameters.
        
        This tool searches for ServiceNow incidents matching the specified criteria.
        All search parameters are optional. If no parameters are provided, returns active incidents.
        
        Args:
            **kwargs: Search parameters including:
                - active: Select active records (default True)
                - requested_by: Search by incident requestor name
                - company: Search by company value
                - service_name: Search by service name
                - category: Search by category (e.g., "Performance")
                - subcategory: Search by subcategory (e.g., "Timeout")
                - configuration_item: Search by Configuration item sys_id
                - state: Search by incident state (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)
                - priority: Search by priority (1=Critical, 2=High, 3=Medium, 4=Low)
                - assignment_group: Search by Assignment Group
                - assigned_to: Search by assigned user
                
        Returns:
            Dictionary containing:
                - success: True if search successful
                - incidents: List of matching incidents
                - count: Number of incidents found
                - message: Search summary
                Or error information if failed
                
        Raises:
            ServiceNowAPIError: For API errors
        """
        try:
            logger.debug("Searching incidents with criteria")
            
            # Build search request data, filtering out None values
            search_data = {k: v for k, v in kwargs.items() if v is not None}
            
            # Set default active=True if not specified
            if "active" not in search_data:
                search_data["active"] = True
            
            # Validate search data with Pydantic model
            try:
                search_request = IncidentSearchRequest(**search_data)
                validated_data = search_request.model_dump(exclude_none=True)
                logger.debug(f"Validated search data: {validated_data}")
            except Exception as e:
                logger.warning(f"Search data validation failed: {e}")
                return {
                    "error": f"Invalid search parameters: {str(e)}",
                    "error_type": "validation_error"
                }
            
            # Make the API call
            search_results = await self.client.search_incidents(validated_data)
            
            # Handle different response formats
            if isinstance(search_results, list):
                incidents = search_results
            elif isinstance(search_results, dict) and "incidents" in search_results:
                incidents = search_results["incidents"]
            elif isinstance(search_results, dict) and "result" in search_results:
                incidents = search_results["result"]
            else:
                incidents = search_results if isinstance(search_results, list) else [search_results]
            
            # Ensure incidents is a list
            if not isinstance(incidents, list):
                incidents = [incidents] if incidents else []
            
            count = len(incidents)
            logger.info(f"Found {count} incidents matching search criteria")
            
            return {
                "success": True,
                "incidents": incidents,
                "count": count,
                "search_criteria": validated_data,
                "message": f"Found {count} incident(s) matching search criteria"
            }
                
        except ServiceNowAPIError as e:
            logger.error(f"API error searching incidents: {e}")
            return {
                "error": str(e),
                "error_type": "api_error",
                "status_code": getattr(e, "status_code", None)
            }
        except Exception as e:
            logger.error(f"Unexpected error searching incidents: {e}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown"
            }