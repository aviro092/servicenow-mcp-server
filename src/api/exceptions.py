"""ServiceNow API exceptions."""


class ServiceNowAPIError(Exception):
    """Base exception for ServiceNow API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ServiceNowAuthError(ServiceNowAPIError):
    """Authentication error with ServiceNow API."""
    pass


class ServiceNowNotFoundError(ServiceNowAPIError):
    """Resource not found error."""
    pass


class ServiceNowRateLimitError(ServiceNowAPIError):
    """Rate limit exceeded error."""
    pass


class ServiceNowValidationError(ServiceNowAPIError):
    """Request validation error."""
    pass