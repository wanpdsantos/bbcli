"""
Bitbucket API client for bbcli.

This module provides a comprehensive client for interacting with the Bitbucket Cloud API,
including OAuth 2.0 authentication, error handling, and rate limiting.
"""

import base64
import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bbcli.core.auth_manager import AuthManager
from bbcli.core.config import get_config
from bbcli.core.exceptions import APIError, AuthenticationError
from bbcli.core.oauth_storage import OAuthStorage


class BitbucketAPIClient:
    """Client for interacting with the Bitbucket Cloud API."""

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        oauth_token: str | None = None,
        prefer_oauth: bool = True,
    ) -> None:
        """
        Initialize the API client.

        Args:
            base_url: Base URL for the Bitbucket API. Defaults to config value.
            username: Bitbucket username. If not provided, will try environment
                     variables or stored credentials.
            password: Bitbucket app password. If not provided, will try environment
                     variables or stored credentials.
            oauth_token: OAuth 2.0 access token. If provided, will be used for authentication.
            prefer_oauth: Whether to prefer OAuth 2.0 over Basic Auth when both are available.
        """
        self.config = get_config()
        self.auth_manager = AuthManager()
        self.oauth_storage = OAuthStorage()
        self.base_url = base_url or self.config.get("api.base_url", "https://api.bitbucket.org/2.0")
        self.timeout = self.config.get("api.timeout", 30)
        self.max_retries = self.config.get("api.max_retries", 3)

        # Store provided credentials
        self._provided_username = username
        self._provided_password = password
        self._provided_oauth_token = oauth_token
        self._prefer_oauth = prefer_oauth

        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set up authentication
        self._setup_auth()

    def _get_credentials(self) -> tuple[str, str] | None:
        """
        Get credentials from various sources in order of priority.

        Priority order:
        1. Constructor parameters
        2. Environment variables
        3. Stored credentials (keyring or encrypted file)

        Returns:
            Tuple of (username, password) or None if no credentials found
        """
        # 1. Check constructor parameters
        if self._provided_username and self._provided_password:
            return self._provided_username, self._provided_password

        # 2. Check environment variables
        env_username = os.getenv("BBCLI_USERNAME")
        env_password = os.getenv("BBCLI_PASSWORD")
        if env_username and env_password:
            return env_username, env_password

        # 3. Check stored credentials
        return self.auth_manager.get_credentials()

    def _get_oauth_token(self) -> str | None:
        """
        Get OAuth token from various sources in order of priority.

        Priority order:
        1. Constructor parameter
        2. Environment variable
        3. Stored token (if valid)

        Returns:
            OAuth access token or None if not available
        """
        # 1. Check constructor parameter
        if self._provided_oauth_token:
            return self._provided_oauth_token

        # 2. Check environment variable
        env_token = os.getenv("BBCLI_OAUTH_TOKEN")
        if env_token:
            return env_token

        # 3. Check stored token (if valid and not expired)
        stored_token = self.oauth_storage.get_valid_token()
        if stored_token:
            return stored_token.access_token

        return None

    def _create_basic_auth_header(self, username: str, password: str) -> str:
        """
        Create Basic Authentication header value.

        Args:
            username: Username for authentication
            password: Password for authentication

        Returns:
            Base64 encoded Basic Auth header value
        """
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        return f"Basic {encoded_credentials}"

    def _setup_auth(self) -> None:
        """Set up authentication for the session."""
        # Authentication is now handled per-request in _make_request method
        # This ensures explicit Basic Auth headers are added to each request
        pass

    def has_credentials(self) -> bool:
        """
        Check if authentication credentials are available.

        Returns:
            True if credentials are available, False otherwise
        """
        return self._get_credentials() is not None or self._get_oauth_token() is not None

    def has_oauth_token(self) -> bool:
        """
        Check if OAuth token is available.

        Returns:
            True if OAuth token is available, False otherwise
        """
        return self._get_oauth_token() is not None

    def is_using_oauth(self) -> bool:
        """
        Check if currently using OAuth authentication.

        Returns:
            True if using OAuth, False if using Basic Auth or no auth
        """
        return self.has_oauth_token() and self._prefer_oauth

    def get_auth_header(self) -> str | None:
        """
        Get the authentication header value (OAuth Bearer or Basic Auth).

        Returns:
            Authentication header value or None if no credentials available
        """
        # Prefer OAuth if available and enabled
        oauth_token = self._get_oauth_token()
        if oauth_token and self._prefer_oauth:
            return f"Bearer {oauth_token}"

        # Fall back to Basic Auth
        credentials = self._get_credentials()
        if credentials:
            username, password = credentials
            return self._create_basic_auth_header(username, password)

        return None

    def validate_credentials(self) -> bool:
        """
        Validate current credentials by making a test API call.

        Returns:
            True if credentials are valid, False otherwise
        """
        if not self.has_credentials():
            return False

        try:
            self.test_authentication()
            return True
        except AuthenticationError:
            return False
        except APIError:
            # Other API errors don't necessarily mean invalid credentials
            return True

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        """
        Make an HTTP request to the Bitbucket API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            data: Form data
            json_data: JSON data
            headers: Additional headers

        Returns:
            Response object

        Raises:
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Prepare headers
        request_headers = {
            "Accept": "application/json",
            "User-Agent": "bbcli/0.1.0",
        }

        # Add authentication header (OAuth Bearer token preferred over Basic Auth)
        oauth_token = self._get_oauth_token()
        if oauth_token and self._prefer_oauth:
            # Use OAuth 2.0 Bearer token
            request_headers["Authorization"] = f"Bearer {oauth_token}"
        else:
            # Fall back to Basic Authentication if available
            credentials = self._get_credentials()
            if credentials:
                username, password = credentials
                auth_header = self._create_basic_auth_header(username, password)
                request_headers["Authorization"] = auth_header

        if headers:
            request_headers.update(headers)
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers,
                timeout=self.timeout,
            )

            # Handle authentication errors
            if response.status_code == 401:
                # Provide more specific error messages based on credential source
                credentials = self._get_credentials()
                if not credentials:
                    error_msg = "No authentication credentials found."
                    suggestion = "Run 'bbcli auth login' to set up authentication"
                elif self._provided_username or self._provided_password:
                    error_msg = "Authentication failed with provided credentials."
                    suggestion = "Check your username and password"
                elif os.getenv("BBCLI_USERNAME") or os.getenv("BBCLI_PASSWORD"):
                    error_msg = "Authentication failed with environment variable credentials."
                    suggestion = "Check BBCLI_USERNAME and BBCLI_PASSWORD environment variables"
                else:
                    error_msg = "Authentication failed with stored credentials."
                    suggestion = "Run 'bbcli auth login' to re-authenticate"

                raise AuthenticationError(error_msg, suggestion=suggestion)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise APIError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    status_code=response.status_code,
                    suggestion=f"Wait {retry_after} seconds before retrying",
                )

            # Handle other client/server errors
            if not response.ok:
                error_data = None
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get("message", "Unknown API error")
                except (ValueError, KeyError):
                    error_message = f"HTTP {response.status_code}: {response.reason}"

                raise APIError(
                    error_message,
                    status_code=response.status_code,
                    response_data=error_data,
                )

            return response

        except requests.exceptions.Timeout as e:
            raise APIError(
                f"Request timed out after {self.timeout} seconds",
                suggestion="Try again or increase the timeout in configuration",
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise APIError(
                "Failed to connect to Bitbucket API",
                suggestion="Check your internet connection and try again",
            ) from e
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}") from e

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request."""
        response = self._make_request("GET", endpoint, params=params)
        return response.json()

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request."""
        response = self._make_request("POST", endpoint, data=data, json_data=json_data)
        return response.json()

    def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PUT request."""
        response = self._make_request("PUT", endpoint, data=data, json_data=json_data)
        return response.json()

    def delete(self, endpoint: str) -> dict[str, Any] | None:
        """Make a DELETE request."""
        response = self._make_request("DELETE", endpoint)
        if response.content:
            return response.json()
        return None

    def test_authentication(self) -> dict[str, Any]:
        """
        Test authentication by fetching user information.

        Returns:
            User information from the API

        Raises:
            AuthenticationError: If authentication fails
        """
        return self.get("/user")

    def get_workspaces(self) -> dict[str, Any]:
        """Get list of workspaces accessible to the authenticated user."""
        return self.get("/workspaces")

    def get_workspace(self, workspace: str) -> dict[str, Any]:
        """Get information about a specific workspace."""
        return self.get(f"/workspaces/{workspace}")


# Global API client instance
_api_client_instance: BitbucketAPIClient | None = None


def get_api_client() -> BitbucketAPIClient:
    """Get the global API client instance."""
    global _api_client_instance
    if _api_client_instance is None:
        _api_client_instance = BitbucketAPIClient()
    return _api_client_instance
