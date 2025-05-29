"""
Tests for API client functionality.
"""

import base64
import os
from unittest.mock import Mock, patch

import pytest
import requests

from bbcli.core.api_client import BitbucketAPIClient
from bbcli.core.exceptions import APIError, AuthenticationError


class TestBitbucketAPIClient:
    """Test cases for BitbucketAPIClient class."""

    @pytest.fixture
    def mock_auth_manager(self):
        """Mock auth manager."""
        with patch("bbcli.core.api_client.AuthManager") as mock:
            mock_instance = mock.return_value
            mock_instance.get_credentials.return_value = ("testuser", "testpass")
            yield mock_instance

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        with patch("bbcli.core.api_client.get_config") as mock:
            config = mock.return_value
            config.get.side_effect = lambda key, default=None: {
                "api.base_url": "https://api.bitbucket.org/2.0",
                "api.timeout": 30,
                "api.max_retries": 3,
            }.get(key, default)
            yield config

    @pytest.fixture
    def api_client(self, mock_auth_manager):
        """Create API client instance."""
        return BitbucketAPIClient()

    def test_initialization(self, api_client):
        """Test API client initialization."""
        assert api_client.base_url == "https://api.bitbucket.org/2.0"
        assert api_client.timeout == 30
        assert api_client.max_retries == 3
        # Verify credentials are available through the new method
        assert api_client.has_credentials() is True
        credentials = api_client._get_credentials()
        assert credentials == ("testuser", "testpass")

    @patch("requests.Session.request")
    def test_successful_get_request(self, mock_request, api_client):
        """Test successful GET request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        result = api_client.get("/test")

        assert result == {"key": "value"}
        mock_request.assert_called_once()

    @patch("requests.Session.request")
    def test_authentication_error(self, mock_request, api_client):
        """Test handling of authentication errors."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        with pytest.raises(AuthenticationError):
            api_client.get("/test")

    @patch("requests.Session.request")
    def test_rate_limit_error(self, mock_request, api_client):
        """Test handling of rate limit errors."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_request.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            api_client.get("/test")

        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.status_code == 429

    @patch("requests.Session.request")
    def test_api_error_with_json_response(self, mock_request, api_client):
        """Test handling of API errors with JSON error response."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Invalid request"}}
        mock_request.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            api_client.get("/test")

        assert "Invalid request" in str(exc_info.value)
        assert exc_info.value.status_code == 400

    @patch("requests.Session.request")
    def test_api_error_without_json_response(self, mock_request, api_client):
        """Test handling of API errors without JSON error response."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_response.json.side_effect = ValueError("No JSON")
        mock_request.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            api_client.get("/test")

        assert "HTTP 500: Internal Server Error" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_timeout_error(self, mock_request, api_client):
        """Test handling of timeout errors."""
        mock_request.side_effect = requests.exceptions.Timeout()

        with pytest.raises(APIError) as exc_info:
            api_client.get("/test")

        assert "timed out" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_connection_error(self, mock_request, api_client):
        """Test handling of connection errors."""
        mock_request.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(APIError) as exc_info:
            api_client.get("/test")

        assert "Failed to connect" in str(exc_info.value)

    @patch("requests.Session.request")
    def test_post_request_with_json_data(self, mock_request, api_client):
        """Test POST request with JSON data."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"created": True}
        mock_request.return_value = mock_response

        result = api_client.post("/test", json_data={"name": "test"})

        assert result == {"created": True}
        args, kwargs = mock_request.call_args
        assert kwargs["json"] == {"name": "test"}

    @patch("requests.Session.request")
    def test_delete_request(self, mock_request, api_client):
        """Test DELETE request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b""
        mock_request.return_value = mock_response

        result = api_client.delete("/test")

        assert result is None
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "DELETE"

    @patch("requests.Session.request")
    def test_test_authentication_success(self, mock_request, api_client):
        """Test successful authentication test."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"username": "testuser"}
        mock_request.return_value = mock_response

        result = api_client.test_authentication()

        assert result == {"username": "testuser"}
        _, kwargs = mock_request.call_args
        assert "/user" in kwargs["url"]


class TestBitbucketAPIClientAuthentication:
    """Test cases for authentication functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        with patch("bbcli.core.api_client.get_config") as mock:
            config = mock.return_value
            config.get.side_effect = lambda key, default=None: {
                "api.base_url": "https://api.bitbucket.org/2.0",
                "api.timeout": 30,
                "api.max_retries": 3,
            }.get(key, default)
            yield config

    def test_initialization_with_credentials(self):
        """Test API client initialization with provided credentials."""
        with patch("bbcli.core.api_client.AuthManager"):
            client = BitbucketAPIClient(username="testuser", password="testpass")
            assert client._provided_username == "testuser"
            assert client._provided_password == "testpass"
            # Verify credentials are available through the new method
            assert client.has_credentials() is True
            credentials = client._get_credentials()
            assert credentials == ("testuser", "testpass")

    def test_get_credentials_priority_constructor(self):
        """Test credential priority: constructor parameters first."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = (
                "stored_user",
                "stored_pass",
            )

            with patch.dict(os.environ, {"BBCLI_USERNAME": "env_user", "BBCLI_PASSWORD": "env_pass"}):
                client = BitbucketAPIClient(username="param_user", password="param_pass")
                credentials = client._get_credentials()
                assert credentials == ("param_user", "param_pass")

    def test_get_credentials_priority_environment(self):
        """Test credential priority: environment variables second."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = (
                "stored_user",
                "stored_pass",
            )

            with patch.dict(os.environ, {"BBCLI_USERNAME": "env_user", "BBCLI_PASSWORD": "env_pass"}):
                client = BitbucketAPIClient()
                credentials = client._get_credentials()
                assert credentials == ("env_user", "env_pass")

    def test_get_credentials_priority_stored(self):
        """Test credential priority: stored credentials last."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = (
                "stored_user",
                "stored_pass",
            )

            with patch.dict(os.environ, {}, clear=True):
                client = BitbucketAPIClient()
                credentials = client._get_credentials()
                assert credentials == ("stored_user", "stored_pass")

    def test_get_credentials_none_available(self):
        """Test when no credentials are available."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            with patch.dict(os.environ, {}, clear=True):
                client = BitbucketAPIClient()
                credentials = client._get_credentials()
                assert credentials is None

    def test_create_basic_auth_header(self):
        """Test Basic Auth header creation."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None
            client = BitbucketAPIClient()
            header = client._create_basic_auth_header("testuser", "testpass")

            expected = base64.b64encode(b"testuser:testpass").decode("ascii")
            assert header == f"Basic {expected}"

    def test_has_credentials_true(self):
        """Test has_credentials returns True when credentials exist."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = ("user", "pass")

            client = BitbucketAPIClient()
            assert client.has_credentials() is True

    def test_has_credentials_false(self):
        """Test has_credentials returns False when no credentials exist."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            client = BitbucketAPIClient()
            assert client.has_credentials() is False

    def test_get_auth_header_with_credentials(self):
        """Test get_auth_header returns header when credentials exist."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = ("user", "pass")

            client = BitbucketAPIClient()
            header = client.get_auth_header()

            expected = base64.b64encode(b"user:pass").decode("ascii")
            assert header == f"Basic {expected}"

    def test_get_auth_header_without_credentials(self):
        """Test get_auth_header returns None when no credentials exist."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            client = BitbucketAPIClient()
            header = client.get_auth_header()
            assert header is None

    @patch("requests.Session.request")
    def test_validate_credentials_success(self, mock_request):
        """Test validate_credentials returns True for valid credentials."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = ("user", "pass")

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"username": "user"}
            mock_request.return_value = mock_response

            client = BitbucketAPIClient()
            assert client.validate_credentials() is True

    @patch("requests.Session.request")
    def test_validate_credentials_auth_failure(self, mock_request):
        """Test validate_credentials returns False for invalid credentials."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = ("user", "pass")

            mock_response = Mock()
            mock_response.ok = False
            mock_response.status_code = 401
            mock_request.return_value = mock_response

            client = BitbucketAPIClient()
            assert client.validate_credentials() is False

    def test_validate_credentials_no_credentials(self):
        """Test validate_credentials returns False when no credentials exist."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            client = BitbucketAPIClient()
            assert client.validate_credentials() is False

    @patch("requests.Session.request")
    def test_enhanced_auth_error_no_credentials(self, mock_request):
        """Test enhanced authentication error message when no credentials found."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            mock_response = Mock()
            mock_response.ok = False
            mock_response.status_code = 401
            mock_request.return_value = mock_response

            client = BitbucketAPIClient()

            with pytest.raises(AuthenticationError) as exc_info:
                client.get("/test")

            assert "No authentication credentials found" in str(exc_info.value)
            assert "bbcli auth login" in exc_info.value.suggestion

    @patch("requests.Session.request")
    def test_enhanced_auth_error_provided_credentials(self, mock_request):
        """Test enhanced authentication error message for provided credentials."""
        with patch("bbcli.core.api_client.AuthManager"):
            mock_response = Mock()
            mock_response.ok = False
            mock_response.status_code = 401
            mock_request.return_value = mock_response

            client = BitbucketAPIClient(username="user", password="pass")

            with pytest.raises(AuthenticationError) as exc_info:
                client.get("/test")

            assert "Authentication failed with provided credentials" in str(exc_info.value)
            assert "Check your username and password" in exc_info.value.suggestion

    @patch("requests.Session.request")
    def test_enhanced_auth_error_environment_credentials(self, mock_request):
        """Test enhanced authentication error message for environment credentials."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            mock_response = Mock()
            mock_response.ok = False
            mock_response.status_code = 401
            mock_request.return_value = mock_response

            with patch.dict(os.environ, {"BBCLI_USERNAME": "user", "BBCLI_PASSWORD": "pass"}):
                client = BitbucketAPIClient()

                with pytest.raises(AuthenticationError) as exc_info:
                    client.get("/test")

                assert "Authentication failed with environment variable credentials" in str(exc_info.value)
                assert "BBCLI_USERNAME and BBCLI_PASSWORD" in exc_info.value.suggestion

    @patch("requests.Session.request")
    def test_enhanced_auth_error_stored_credentials(self, mock_request):
        """Test enhanced authentication error message for stored credentials."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = ("user", "pass")

            mock_response = Mock()
            mock_response.ok = False
            mock_response.status_code = 401
            mock_request.return_value = mock_response

            with patch.dict(os.environ, {}, clear=True):
                client = BitbucketAPIClient()

                with pytest.raises(AuthenticationError) as exc_info:
                    client.get("/test")

                assert "Authentication failed with stored credentials" in str(exc_info.value)
                assert "bbcli auth login" in exc_info.value.suggestion

    @patch("requests.Session.request")
    def test_authorization_header_added_to_request(self, mock_request):
        """Test that Authorization header is explicitly added to requests."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = (
                "testuser",
                "testpass",
            )

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response

            client = BitbucketAPIClient()
            client.get("/test")

            # Verify the request was called with Authorization header
            _, kwargs = mock_request.call_args
            headers = kwargs["headers"]

            # Check that Authorization header is present
            assert "Authorization" in headers

            # Verify it's a Basic Auth header with correct format
            auth_header = headers["Authorization"]
            assert auth_header.startswith("Basic ")

            # Verify the encoded credentials are correct
            expected_credentials = base64.b64encode(b"testuser:testpass").decode("ascii")
            expected_header = f"Basic {expected_credentials}"
            assert auth_header == expected_header

    @patch("requests.Session.request")
    def test_no_authorization_header_without_credentials(self, mock_request):
        """Test that no Authorization header is added when no credentials are available."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response

            client = BitbucketAPIClient()
            client.get("/test")

            # Verify the request was called without Authorization header
            _, kwargs = mock_request.call_args
            headers = kwargs["headers"]

            # Check that Authorization header is not present
            assert "Authorization" not in headers

    @patch("requests.Session.request")
    def test_oauth_bearer_token_authentication(self, mock_request):
        """Test that OAuth Bearer token is used when provided."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response

            # Create client with OAuth token
            client = BitbucketAPIClient(oauth_token="test_oauth_token")
            client.get("/test")

            # Verify the request was called with Bearer token
            _, kwargs = mock_request.call_args
            headers = kwargs["headers"]

            assert "Authorization" in headers
            auth_header = headers["Authorization"]
            assert auth_header == "Bearer test_oauth_token"

    @patch("requests.Session.request")
    def test_oauth_preference_over_basic_auth(self, mock_request):
        """Test that OAuth is preferred over Basic Auth when both are available."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = ("user", "pass")

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response

            # Create client with both OAuth token and Basic Auth credentials
            client = BitbucketAPIClient(
                username="user",
                password="pass",
                oauth_token="test_oauth_token",
                prefer_oauth=True,
            )
            client.get("/test")

            # Verify OAuth Bearer token is used instead of Basic Auth
            _, kwargs = mock_request.call_args
            headers = kwargs["headers"]

            assert "Authorization" in headers
            auth_header = headers["Authorization"]
            assert auth_header == "Bearer test_oauth_token"
            assert not auth_header.startswith("Basic ")

    @patch("requests.Session.request")
    def test_basic_auth_when_oauth_disabled(self, mock_request):
        """Test that Basic Auth is used when OAuth is disabled."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = ("user", "pass")

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"result": "success"}
            mock_request.return_value = mock_response

            # Create client with OAuth disabled
            client = BitbucketAPIClient(
                username="user",
                password="pass",
                oauth_token="test_oauth_token",
                prefer_oauth=False,
            )
            client.get("/test")

            # Verify Basic Auth is used instead of OAuth
            _, kwargs = mock_request.call_args
            headers = kwargs["headers"]

            assert "Authorization" in headers
            auth_header = headers["Authorization"]
            assert auth_header.startswith("Basic ")
            assert not auth_header.startswith("Bearer ")

    def test_oauth_helper_methods(self):
        """Test OAuth-related helper methods."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            # Test with OAuth token
            client = BitbucketAPIClient(oauth_token="test_token")
            assert client.has_oauth_token() is True
            assert client.is_using_oauth() is True
            assert client.has_credentials() is True

            # Test without OAuth token
            client = BitbucketAPIClient()
            assert client.has_oauth_token() is False
            assert client.is_using_oauth() is False

    def test_get_auth_header_oauth(self):
        """Test get_auth_header returns OAuth Bearer token when available."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = None

            client = BitbucketAPIClient(oauth_token="test_token")
            auth_header = client.get_auth_header()
            assert auth_header == "Bearer test_token"

    def test_get_auth_header_preference(self):
        """Test get_auth_header respects OAuth preference."""
        with patch("bbcli.core.api_client.AuthManager") as mock_auth:
            mock_auth.return_value.get_credentials.return_value = ("user", "pass")

            # Test OAuth preferred
            client = BitbucketAPIClient(
                username="user",
                password="pass",
                oauth_token="test_token",
                prefer_oauth=True,
            )
            auth_header = client.get_auth_header()
            assert auth_header == "Bearer test_token"

            # Test Basic Auth preferred
            client = BitbucketAPIClient(
                username="user",
                password="pass",
                oauth_token="test_token",
                prefer_oauth=False,
            )
            auth_header = client.get_auth_header()
            assert auth_header.startswith("Basic ")
