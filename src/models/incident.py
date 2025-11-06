"""Incident data models."""

from typing import List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ResolutionInfo(BaseModel):
    """Resolution information for an incident."""
    
    resolution_code: Optional[str] = Field(None, description="Incident closed code details")
    resolution_notes: Optional[str] = Field(None, description="Incident resolution notes")
    resolved_at: Optional[str] = Field(None, description="Incident resolved date")
    resolved_by: Optional[str] = Field(None, description="User who resolved the incident")
    knowledge: Optional[Union[str, bool]] = Field(None, description="Mapped knowledge article info")


class IncidentTask(BaseModel):
    """Incident task model."""
    
    task_number: str = Field(..., description="CMSP ServiceNow Incident task number")
    state: Optional[str] = Field(None, description="Incident task record current state")
    short_description: str = Field(..., max_length=120, description="Incident task short description")
    configuration_item: Optional[str] = Field(None, description="Configuration item sys_id")
    business_service: Optional[str] = Field(None, description="Service name")
    assignment_group: Optional[str] = Field(None, description="Assignment Group sys_id")
    assigned_to: Optional[str] = Field(None, description="Assigned user")


class IncidentResponse(BaseModel):
    """Complete incident response model."""
    
    number: str = Field(..., description="CMSP ServiceNow ticket number")
    requested_by: str = Field(..., description="Creator of the ServiceNow ticket")
    company: str = Field(..., description="Account mapped in CMSP ServiceNow")
    service_name: str = Field(..., description="Service name mapped to cmdb_ci_service")
    category: Optional[str] = Field(None, description="Category details")
    subcategory: Optional[str] = Field(None, description="Sub-Category details")
    configuration_item: str = Field(..., description="Configuration item sys_id")
    source: Optional[str] = Field(None, description="Incident creation source")
    state: str = Field(..., description="Incident current state")
    impact: Optional[str] = Field(None, description="Incident impact value")
    urgency: str = Field(..., description="Incident urgency value")
    priority: Optional[str] = Field(None, description="Incident priority value")
    assignment_group: Optional[str] = Field(None, description="Assignment Group sys_id")
    assigned_to: Optional[str] = Field(None, description="Assigned user")
    short_description: str = Field(..., max_length=120, description="Incident short description")
    description: Optional[str] = Field(None, max_length=4000, description="Incident description")
    comments: Optional[str] = Field(None, description="Last updated comments")
    notes: Optional[str] = Field(None, description="Last updated notes")
    created_by: str = Field(..., description="Created user email")
    created_date: str = Field(..., description="Incident created date")
    modified_by: str = Field(..., description="Last modified user")
    modified_date: str = Field(..., description="Last modified date")
    closed_by: Optional[str] = Field(None, description="Incident closed user")
    closed_date: Optional[str] = Field(None, description="Incident closed date")
    resolution_info: Optional[ResolutionInfo] = Field(None, description="Resolution information")
    customer_reference_id: Optional[str] = Field(None, description="Customer Incident ticket ID")
    incident_tasks: Optional[List[IncidentTask]] = Field(default_factory=list, description="Child incident tasks")
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Convert state code to readable format if needed."""
        state_map = {
            "1": "New",
            "2": "In Progress",
            "3": "On Hold",
            "6": "Resolved",
            "7": "Closed",
            "8": "Canceled"
        }
        return state_map.get(v, v)
    
    @field_validator("impact", "urgency", "priority")
    @classmethod
    def validate_priority_fields(cls, v: Optional[str]) -> Optional[str]:
        """Convert priority field codes to readable format if needed."""
        if not v:
            return v
            
        priority_map = {
            "1": "1 - Critical",
            "2": "2 - High",
            "3": "3 - Medium",
            "4": "4 - Low"
        }
        return priority_map.get(v, v)
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        }
    }


class IncidentUpdateRequest(BaseModel):
    """Incident update request model with all updatable fields."""
    
    number: str = Field(..., description="CMSP ServiceNow ticket number")
    state: Optional[Union[int, str]] = Field(None, description="Incident record current state (1-8)")
    impact: Optional[Union[int, str]] = Field(None, description="Incident impact value (1-4)")
    urgency: Optional[Union[int, str]] = Field(None, description="Incident urgency value (1-4)")
    category: Optional[str] = Field(None, description="Category details from sys_choice table")
    subcategory: Optional[str] = Field(None, description="Sub-Category details from sys_choice table")
    short_description: Optional[str] = Field(None, max_length=120, description="Incident short description")
    description: Optional[str] = Field(None, max_length=4000, description="Incident description details")
    holdreason: Optional[str] = Field(None, description="Reason for putting the Incident ticket to hold state")
    service_impacting: Optional[str] = Field(None, description="Impacted Service details")
    comments: Optional[str] = Field(None, description="Add comments to Incident Record")
    notes: Optional[str] = Field(None, description="Add notes to Incident Record")
    customer_reference_id: Optional[str] = Field(None, description="Customer Incident ticket ID")
    resolution_info: Optional[ResolutionInfo] = Field(None, description="Resolution information")
    
    @field_validator("state")
    @classmethod
    def validate_state_update(cls, v: Optional[Union[int, str]]) -> Optional[Union[int, str]]:
        """Validate state value for updates."""
        if v is None:
            return v
        
        # Convert string state names to numbers for API
        if isinstance(v, str):
            state_map = {
                "new": 1,
                "in progress": 2,
                "on hold": 3,
                "resolved": 6,
                "closed": 7,
                "canceled": 8
            }
            lower_v = v.lower()
            if lower_v in state_map:
                return state_map[lower_v]
        
        # Validate numeric states
        if isinstance(v, (int, str)):
            try:
                state_int = int(v)
                if state_int in [1, 2, 3, 6, 7, 8]:
                    return state_int
                else:
                    raise ValueError(f"Invalid state value: {v}. Must be 1, 2, 3, 6, 7, or 8")
            except ValueError:
                raise ValueError(f"Invalid state value: {v}")
        
        return v
    
    @field_validator("impact", "urgency")
    @classmethod
    def validate_priority_fields_update(cls, v: Optional[Union[int, str]]) -> Optional[Union[int, str]]:
        """Validate impact and urgency values for updates."""
        if v is None:
            return v
        
        # Convert string priority names to numbers for API
        if isinstance(v, str):
            priority_map = {
                "critical": 1,
                "high": 2,
                "medium": 3,
                "low": 4
            }
            lower_v = v.lower()
            if lower_v in priority_map:
                return priority_map[lower_v]
        
        # Validate numeric priorities
        if isinstance(v, (int, str)):
            try:
                priority_int = int(v)
                if priority_int in [1, 2, 3, 4]:
                    return priority_int
                else:
                    raise ValueError(f"Invalid priority value: {v}. Must be 1, 2, 3, or 4")
            except ValueError:
                raise ValueError(f"Invalid priority value: {v}")
        
        return v


class IncidentCreateRequest(BaseModel):
    """Incident creation request model with all creatable fields."""
    
    # Required fields
    short_description: str = Field(..., max_length=120, description="Incident short description")
    description: str = Field(..., max_length=4000, description="Incident description details")
    service_name: str = Field(..., description="Service name mapped to cmdb_ci_service table")
    urgency: Union[int, str] = Field(..., description="Incident urgency value (1-4)")
    
    # Optional fields
    impact: Optional[Union[int, str]] = Field(None, description="Incident impact value (1-4)")
    category: Optional[str] = Field(None, description="Category details from sys_choice table")
    subcategory: Optional[str] = Field(None, description="Subcategory details from sys_choice table")
    configuration_item: Optional[str] = Field(None, description="Configuration item sys_id")
    assigned_to: Optional[str] = Field(None, description="Assigned user sys_id")
    assignment_group: Optional[str] = Field(None, description="Assignment group")
    contact_type: Optional[str] = Field(None, description="Type of interface used to create Incident")
    customer_reference_id: Optional[str] = Field(None, description="Customer Incident ticket ID")
    
    @field_validator("urgency")
    @classmethod
    def validate_urgency_create(cls, v: Union[int, str]) -> int:
        """Validate urgency value for creation (required field)."""
        if v is None:
            raise ValueError("Urgency is required for incident creation")
        
        # Convert string priority names to numbers for API
        if isinstance(v, str):
            priority_map = {
                "critical": 1,
                "high": 2,
                "medium": 3,
                "low": 4
            }
            lower_v = v.lower()
            if lower_v in priority_map:
                return priority_map[lower_v]
        
        # Validate numeric priorities
        if isinstance(v, (int, str)):
            try:
                priority_int = int(v)
                if priority_int in [1, 2, 3, 4]:
                    return priority_int
                else:
                    raise ValueError(f"Invalid urgency value: {v}. Must be 1, 2, 3, or 4")
            except ValueError:
                raise ValueError(f"Invalid urgency value: {v}")
        
        raise ValueError(f"Invalid urgency value: {v}")
    
    @field_validator("impact")
    @classmethod
    def validate_impact_create(cls, v: Optional[Union[int, str]]) -> Optional[int]:
        """Validate impact value for creation."""
        if v is None:
            return v
        
        # Convert string priority names to numbers for API
        if isinstance(v, str):
            priority_map = {
                "critical": 1,
                "high": 2,
                "medium": 3,
                "low": 4
            }
            lower_v = v.lower()
            if lower_v in priority_map:
                return priority_map[lower_v]
        
        # Validate numeric priorities
        if isinstance(v, (int, str)):
            try:
                priority_int = int(v)
                if priority_int in [1, 2, 3, 4]:
                    return priority_int
                else:
                    raise ValueError(f"Invalid impact value: {v}. Must be 1, 2, 3, or 4")
            except ValueError:
                raise ValueError(f"Invalid impact value: {v}")
        
        return v


class IncidentSearchRequest(BaseModel):
    """Incident search request model with all searchable fields."""
    
    # Search parameters (all optional)
    active: Optional[bool] = Field(True, description="Select active records (default true)")
    requested_by: Optional[str] = Field(None, description="Search by incident requestor name")
    company: Optional[str] = Field(None, description="Search by company value")
    service_name: Optional[str] = Field(None, description="Search by service name from cmdb_ci_service")
    category: Optional[str] = Field(None, description="Search by category value from sys_choice")
    subcategory: Optional[str] = Field(None, description="Search by subcategory value from sys_choice")
    configuration_item: Optional[str] = Field(None, description="Search by Configuration item sys_id")
    state: Optional[Union[int, str]] = Field(None, description="Search by incident state (1-8)")
    priority: Optional[Union[int, str]] = Field(None, description="Search by incident priority (1-4)")
    assignment_group: Optional[str] = Field(None, description="Search by Assignment Group sys_id")
    assigned_to: Optional[str] = Field(None, description="Search by assigned user")
    
    @field_validator("state")
    @classmethod
    def validate_state_search(cls, v: Optional[Union[int, str]]) -> Optional[Union[int, str]]:
        """Validate state value for search."""
        if v is None:
            return v
        
        # Convert string state names to numbers for API
        if isinstance(v, str):
            state_map = {
                "new": 1,
                "in progress": 2,
                "on hold": 3,
                "resolved": 6,
                "closed": 7,
                "canceled": 8
            }
            lower_v = v.lower()
            if lower_v in state_map:
                return state_map[lower_v]
        
        # Validate numeric states
        if isinstance(v, (int, str)):
            try:
                state_int = int(v)
                if state_int in [1, 2, 3, 6, 7, 8]:
                    return state_int
                else:
                    raise ValueError(f"Invalid state value: {v}. Must be 1, 2, 3, 6, 7, or 8")
            except ValueError:
                raise ValueError(f"Invalid state value: {v}")
        
        return v
    
    @field_validator("priority")
    @classmethod
    def validate_priority_search(cls, v: Optional[Union[int, str]]) -> Optional[Union[int, str]]:
        """Validate priority value for search."""
        if v is None:
            return v
        
        # Convert string priority names to numbers for API
        if isinstance(v, str):
            priority_map = {
                "critical": 1,
                "high": 2,
                "medium": 3,
                "low": 4
            }
            lower_v = v.lower()
            if lower_v in priority_map:
                return priority_map[lower_v]
        
        # Validate numeric priorities
        if isinstance(v, (int, str)):
            try:
                priority_int = int(v)
                if priority_int in [1, 2, 3, 4]:
                    return priority_int
                else:
                    raise ValueError(f"Invalid priority value: {v}. Must be 1, 2, 3, or 4")
            except ValueError:
                raise ValueError(f"Invalid priority value: {v}")
        
        return v