"""Change Request data models."""

from typing import List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ChangeRequestSearchRequest(BaseModel):
    """Model for change request search parameters."""
    
    active: Optional[bool] = Field(
        True,
        description="Select active records (default value is true)"
    )
    
    requested_by: Optional[str] = Field(
        None,
        description="Search by Change Request's Requestor name"
    )
    
    agreement_id: Optional[str] = Field(
        None,
        description="Search by Change Request's Agreement Id"
    )
    
    company: Optional[str] = Field(
        None,
        description="Search by Change Request's Company"
    )
    
    category: Optional[str] = Field(
        None,
        description="Search by Change Request's Category"
    )
    
    cmdb_ci: Optional[str] = Field(
        None,
        description="Search by Change Request's CMDB CI"
    )
    
    type: Optional[str] = Field(
        None,
        description="Search by Change Request's type"
    )
    
    priority: Optional[int] = Field(
        None,
        description="Search by Change Request's priority (1=Critical, 2=High, 3=Medium, 4=Low)"
    )
    
    risk: Optional[int] = Field(
        None,
        description="Search by Change Request's risk (1-5)"
    )
    
    impact: Optional[int] = Field(
        None,
        description="Search by Change Request's impact (1=Critical, 2=High, 3=Medium, 4=Low)"
    )
    
    state: Optional[int] = Field(
        None,
        description="Search by Change Request's state (1-8)"
    )
    
    assignment_group: Optional[str] = Field(
        None,
        description="Search by Assignment Group mapped to sys_user_group table entries"
    )
    
    assigned_to: Optional[str] = Field(
        None,
        description="Search by Assigned user details mapped to sys_user table entries"
    )
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[int]) -> Optional[int]:
        """Validate priority is within valid range."""
        if v is not None and not (1 <= v <= 4):
            raise ValueError("Priority must be between 1 and 4")
        return v
    
    @field_validator("risk")
    @classmethod
    def validate_risk(cls, v: Optional[int]) -> Optional[int]:
        """Validate risk is within valid range."""
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Risk must be between 1 and 5")
        return v
    
    @field_validator("impact")
    @classmethod
    def validate_impact(cls, v: Optional[int]) -> Optional[int]:
        """Validate impact is within valid range."""
        if v is not None and not (1 <= v <= 4):
            raise ValueError("Impact must be between 1 and 4")
        return v
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[int]) -> Optional[int]:
        """Validate state is within valid range."""
        if v is not None and not (1 <= v <= 8):
            raise ValueError("State must be between 1 and 8")
        return v


class ChangeRequestResponse(BaseModel):
    """Model for a single change request response."""
    
    number: Optional[str] = Field(None, description="Change request number")
    sys_id: Optional[str] = Field(None, description="System ID")
    state: Optional[Union[str, int]] = Field(None, description="Change request state")
    priority: Optional[Union[str, int]] = Field(None, description="Priority level")
    risk: Optional[Union[str, int]] = Field(None, description="Risk level")
    impact: Optional[Union[str, int]] = Field(None, description="Impact level")
    type: Optional[str] = Field(None, description="Change request type")
    category: Optional[str] = Field(None, description="Category")
    company: Optional[str] = Field(None, description="Company")
    requested_by: Optional[str] = Field(None, description="Requested by")
    short_description: Optional[str] = Field(None, description="Short description")
    description: Optional[str] = Field(None, description="Full description")
    assignment_group: Optional[str] = Field(None, description="Assignment group")
    assigned_to: Optional[str] = Field(None, description="Assigned to")
    cmdb_ci: Optional[str] = Field(None, description="CMDB CI")
    agreement_id: Optional[str] = Field(None, description="Agreement ID")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")
    created_on: Optional[str] = Field(None, description="Created on")
    updated_on: Optional[str] = Field(None, description="Updated on")
    closed_at: Optional[str] = Field(None, description="Closed at")
    work_notes: Optional[str] = Field(None, description="Work notes")
    comments: Optional[str] = Field(None, description="Comments")
    
    # Additional fields that might be present in the response
    active: Optional[bool] = Field(None, description="Active status")
    approval: Optional[str] = Field(None, description="Approval status")
    business_duration: Optional[str] = Field(None, description="Business duration")
    calendar_duration: Optional[str] = Field(None, description="Calendar duration")
    close_code: Optional[str] = Field(None, description="Close code")
    correlation_display: Optional[str] = Field(None, description="Correlation display")
    delivery_plan: Optional[str] = Field(None, description="Delivery plan")
    delivery_task: Optional[str] = Field(None, description="Delivery task")
    opened_at: Optional[str] = Field(None, description="Opened at")
    opened_by: Optional[str] = Field(None, description="Opened by")
    phase: Optional[str] = Field(None, description="Phase")
    phase_state: Optional[str] = Field(None, description="Phase state")
    reason: Optional[str] = Field(None, description="Reason")
    review_date: Optional[str] = Field(None, description="Review date")
    review_status: Optional[str] = Field(None, description="Review status")
    test_plan: Optional[str] = Field(None, description="Test plan")
    implementation_plan: Optional[str] = Field(None, description="Implementation plan")
    backout_plan: Optional[str] = Field(None, description="Backout plan")
    urgency: Optional[Union[str, int]] = Field(None, description="Urgency level")


class ChangeRequestUpdateRequest(BaseModel):
    """Model for change request update parameters."""
    
    company_name: str = Field(
        ...,
        description="Company name from company record - REQUIRED"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description for change request"
    )
    
    comments: Optional[str] = Field(
        None,
        description="New comment to be added to change request"
    )
    
    on_hold: Optional[bool] = Field(
        None,
        description="Whether to put change request on hold or not"
    )
    
    on_hold_reason: Optional[str] = Field(
        None,
        description="Reason for putting change request on hold"
    )
    
    resolved: Optional[bool] = Field(
        None,
        description="Whether to mark change request as resolved or not"
    )
    
    customer_reference_id: Optional[str] = Field(
        None,
        description="Customer Change Request number"
    )


class ChangeRequestUpdateResponse(BaseModel):
    """Model for change request update response."""
    
    success: bool = Field(description="Whether the update was successful")
    updated_changerequest: Optional[ChangeRequestResponse] = Field(None, description="Updated change request data")
    changerequest_number: Optional[str] = Field(None, description="Change request number that was updated")
    message: Optional[str] = Field(None, description="Success message")
    error: Optional[str] = Field(None, description="Error message if any")
    error_type: Optional[str] = Field(None, description="Type of error")


class ChangeRequestApprovalRequest(BaseModel):
    """Model for change request approval/rejection parameters."""
    
    state: str = Field(
        ...,
        description="Either 'approved' or 'rejected' are the valid states"
    )
    
    approver_email: str = Field(
        ...,
        description="Email id of the approver user"
    )
    
    approver_name: Optional[str] = Field(
        None,
        description="User name who approved/rejected the CR"
    )
    
    on_behalf: Optional[str] = Field(
        None,
        description="API service account used for approving CR"
    )
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate state is either approved or rejected."""
        if v.lower() not in ["approved", "rejected"]:
            raise ValueError("State must be either 'approved' or 'rejected'")
        return v.lower()


class ChangeRequestApprovalResponse(BaseModel):
    """Model for change request approval response."""
    
    success: bool = Field(description="Whether the approval was successful")
    changerequest_number: str = Field(description="Change request number that was approved/rejected")
    approval_state: str = Field(description="The approval state applied (approved/rejected)")
    approver_email: str = Field(description="Email of the approver")
    message: Optional[str] = Field(None, description="Success message")
    error: Optional[str] = Field(None, description="Error message if any")
    error_type: Optional[str] = Field(None, description="Type of error")


class ChangeRequestSearchResponse(BaseModel):
    """Model for change request search response."""
    
    success: bool = Field(description="Whether the search was successful")
    count: int = Field(description="Number of change requests found")
    change_requests: List[ChangeRequestResponse] = Field(description="List of change requests")
    search_criteria: dict = Field(description="Search criteria used")
    message: Optional[str] = Field(None, description="Response message")
    error: Optional[str] = Field(None, description="Error message if any")
    error_type: Optional[str] = Field(None, description="Type of error")