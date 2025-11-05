"""Incident Task data models."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class IncidentTaskResponse(BaseModel):
    """Model for a single incident task response."""
    
    incident_number: Optional[str] = Field(None, description="CMSP ServiceNOW ticket number")
    incident_short_description: Optional[str] = Field(None, description="Incident short description")
    severity: Optional[str] = Field(None, description="Incident task record current severity value")
    task_number: Optional[str] = Field(None, description="Task number")
    task_short_description: Optional[str] = Field(None, description="Incident task short description")
    created: Optional[str] = Field(None, description="Incident created date")
    configuration_item: Optional[str] = Field(None, description="Configuration item mapped to cmdb_ci table entry")
    url: Optional[str] = Field(None, description="Direct URL to the incident task in ServiceNow")
    
    # Additional fields that might be present in the response
    sys_id: Optional[str] = Field(None, description="System ID")
    state: Optional[str] = Field(None, description="Task state")
    priority: Optional[str] = Field(None, description="Priority level")
    assignment_group: Optional[str] = Field(None, description="Assignment group")
    assigned_to: Optional[str] = Field(None, description="Assigned to")
    updated_on: Optional[str] = Field(None, description="Updated on")
    closed_at: Optional[str] = Field(None, description="Closed at")
    work_notes: Optional[str] = Field(None, description="Work notes")
    comments: Optional[str] = Field(None, description="Comments")
    description: Optional[str] = Field(None, description="Full description")


class IncidentTaskUpdateRequest(BaseModel):
    """Model for incident task update parameters."""
    
    short_description: str = Field(
        ...,
        description="Incident task short description - REQUIRED",
        max_length=120
    )
    
    state: int = Field(
        ...,
        description="Incident task record current state - REQUIRED (1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled)"
    )
    
    description: Optional[str] = Field(
        None,
        description="Incident task description details",
        max_length=4000
    )
    
    priority: Optional[int] = Field(
        None,
        description="Incident task record priority value (1=Critical, 2=High, 3=Medium, 4=Low)"
    )
    
    assignment_group: Optional[str] = Field(
        None,
        description="Assignment Group mapped to sys_user_group table entries"
    )
    
    assigned_to: Optional[str] = Field(
        None,
        description="Assigned user details mapped to sys_user table entries"
    )
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v: int) -> int:
        """Validate state is within valid range."""
        if v not in [1, 2, 3, 6, 7, 8]:
            raise ValueError("State must be one of: 1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled")
        return v
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[int]) -> Optional[int]:
        """Validate priority is within valid range."""
        if v is not None and not (1 <= v <= 4):
            raise ValueError("Priority must be between 1 and 4")
        return v


class IncidentTaskCreateRequest(BaseModel):
    """Model for incident task creation parameters."""
    
    incident_number: str = Field(
        ...,
        description="Parent Incident Number - REQUIRED"
    )
    
    short_description: str = Field(
        ...,
        description="Incident task short description - REQUIRED",
        max_length=120
    )
    
    service_name: str = Field(
        ...,
        description="Agreement Id is mapped to cmdb_ci_service table - REQUIRED"
    )
    
    company_name: str = Field(
        ...,
        description="Incident task associated account details - REQUIRED"
    )
    
    configuration_item: str = Field(
        ...,
        description="Configuration item mapped to cmdb_ci table entry - REQUIRED"
    )
    
    description: Optional[str] = Field(
        None,
        description="Incident task description details",
        max_length=4000
    )
    
    priority: Optional[int] = Field(
        None,
        description="Incident task record priority value (1=Critical, 2=High, 3=Medium, 4=Low)"
    )
    
    assignment_group: Optional[str] = Field(
        None,
        description="Assignment Group mapped to sys_user_group table entries"
    )
    
    assigned_to: Optional[str] = Field(
        None,
        description="Assigned user details mapped to sys_user table entries"
    )
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[int]) -> Optional[int]:
        """Validate priority is within valid range."""
        if v is not None and not (1 <= v <= 4):
            raise ValueError("Priority must be between 1 and 4")
        return v


class IncidentTaskCreateResponse(BaseModel):
    """Model for incident task creation response."""
    
    success: bool = Field(description="Whether the creation was successful")
    created_incident_task: Optional[IncidentTaskResponse] = Field(None, description="Created incident task data")
    task_number: Optional[str] = Field(None, description="Task number that was created")
    message: Optional[str] = Field(None, description="Success message")
    error: Optional[str] = Field(None, description="Error message if any")
    error_type: Optional[str] = Field(None, description="Type of error")


class IncidentTaskUpdateResponse(BaseModel):
    """Model for incident task update response."""
    
    success: bool = Field(description="Whether the update was successful")
    updated_incident_task: Optional[IncidentTaskResponse] = Field(None, description="Updated incident task data")
    task_number: Optional[str] = Field(None, description="Task number that was updated")
    message: Optional[str] = Field(None, description="Success message")
    error: Optional[str] = Field(None, description="Error message if any")
    error_type: Optional[str] = Field(None, description="Type of error")


class IncidentTaskGetResponse(BaseModel):
    """Model for incident task get response."""
    
    success: bool = Field(description="Whether the operation was successful")
    incident_task: Optional[IncidentTaskResponse] = Field(None, description="Incident task data")
    message: Optional[str] = Field(None, description="Success message")
    error: Optional[str] = Field(None, description="Error message if any")
    error_type: Optional[str] = Field(None, description="Type of error")