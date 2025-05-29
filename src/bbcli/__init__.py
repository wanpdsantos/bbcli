"""
bbcli - A command-line interface for interacting with the Bitbucket API.

This package provides a comprehensive CLI tool for managing Bitbucket projects,
repositories, users, and branch permissions through the Bitbucket Cloud API.
"""

__version__ = "0.1.0"
__author__ = "Wanderson Pinto"
__email__ = "wanpdsantos@gmail.com"
__description__ = "A command-line interface for interacting with the Bitbucket API"

# Package-level imports for convenience
from bbcli.core.exceptions import APIError, AuthenticationError, BBCLIError

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "BBCLIError",
    "AuthenticationError",
    "APIError",
]
