"""
Custom exceptions for bbcli.

This module defines all custom exceptions used throughout the bbcli application,
providing structured error handling with appropriate exit codes and user-friendly messages.
"""


class BBCLIError(Exception):
    """Base exception for all bbcli errors."""

    def __init__(
        self,
        message: str,
        exit_code: int = 1,
        suggestion: str | None = None,
    ) -> None:
        """
        Initialize a bbcli error.

        Args:
            message: The error message to display to the user
            exit_code: The exit code to use when terminating the program
            suggestion: Optional suggestion for how to resolve the error
        """
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.suggestion = suggestion

    def __str__(self) -> str:
        return self.message


class AuthenticationError(BBCLIError):
    """Raised when authentication fails or credentials are invalid."""

    def __init__(
        self,
        message: str = "Authentication failed",
        suggestion: str | None = None,
    ) -> None:
        if suggestion is None:
            suggestion = "Run 'bbcli auth login' to set up authentication"
        super().__init__(message, exit_code=2, suggestion=suggestion)


class APIError(BBCLIError):
    """Raised when the Bitbucket API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict | None = None,
        suggestion: str | None = None,
    ) -> None:
        """
        Initialize an API error.

        Args:
            message: The error message
            status_code: HTTP status code from the API response
            response_data: Raw response data from the API
            suggestion: Optional suggestion for resolution
        """
        self.status_code = status_code
        self.response_data = response_data

        # Enhance message with status code if available
        enhanced_message = f"{message} (HTTP {status_code})" if status_code else message

        super().__init__(enhanced_message, exit_code=3, suggestion=suggestion)


class ValidationError(BBCLIError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, exit_code=4, suggestion=suggestion)


class ResourceNotFoundError(BBCLIError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        suggestion: str | None = None,
    ) -> None:
        message = f"{resource_type} '{resource_id}' not found"
        if suggestion is None:
            suggestion = f"Check that the {resource_type.lower()} exists and you have permission to access it"
        super().__init__(message, exit_code=5, suggestion=suggestion)


class ConfigurationError(BBCLIError):
    """Raised when there's an issue with configuration."""

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message, exit_code=6, suggestion=suggestion)


class PermissionError(BBCLIError):
    """Raised when the user lacks permission for an operation."""

    def __init__(
        self,
        message: str = "Permission denied",
        suggestion: str | None = None,
    ) -> None:
        if suggestion is None:
            suggestion = "Check that you have the required permissions for this operation"
        super().__init__(message, exit_code=7, suggestion=suggestion)
