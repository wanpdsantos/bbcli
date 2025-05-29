"""
Core functionality for bbcli.

This package contains the core components for API interaction, authentication,
configuration management, and exception handling.
"""

from bbcli.core.exceptions import APIError, AuthenticationError, BBCLIError

__all__ = ["BBCLIError", "AuthenticationError", "APIError"]
