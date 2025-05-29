"""
Tests for OAuth authentication CLI commands.
"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from rich.console import Console

from bbcli.cli.auth import auth
from bbcli.core.exceptions import AuthenticationError
from bbcli.core.oauth_manager import OAuthApp, OAuthToken
from bbcli.utils.output import OutputFormatter


class TestOAuthAuthCLI:
    """Test cases for OAuth authentication CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_context(self):
        """Create mock CLI context."""
        console = Console()
        formatter = OutputFormatter("text", console)
        return {
            "console": console,
            "formatter": formatter,
            "verbose": False,
            "output_format": "text",
        }

    @pytest.fixture
    def mock_oauth_app(self):
        """Create mock OAuth app."""
        return OAuthApp(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8080/callback",
            scopes="account,repository",
        )

    @pytest.fixture
    def mock_oauth_token(self):
        """Create mock OAuth token."""
        return OAuthToken(
            access_token="test_access_token",
            token_type="bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="account repository",
        )

    def test_auth_login_no_oauth_app_configured(self, runner, mock_context):
        """Test auth login when no OAuth app is configured."""
        with patch("bbcli.cli.auth.OAuthStorage") as mock_storage:
            mock_storage.return_value.get_oauth_app.return_value = None

            # Mock the basic auth setup to avoid interactive prompts
            with patch("bbcli.cli.auth._setup_basic_auth") as mock_basic_auth:
                result = runner.invoke(auth, ["login", "--no-browser"], obj=mock_context)

                assert result.exit_code == 0
                assert "OAuth Setup Required" in result.output
                assert "falling back to basic authentication" in result.output
                mock_basic_auth.assert_called_once()

    def test_auth_login_with_oauth_app_configured(self, runner, mock_context, mock_oauth_app, mock_oauth_token):
        """Test auth login with OAuth app configured."""
        with (
            patch("bbcli.cli.auth.OAuthStorage") as mock_storage,
            patch("bbcli.cli.auth.OAuthManager") as mock_manager,
            patch("bbcli.cli.auth.OAuthCallbackServer") as mock_server,
            patch("bbcli.cli.auth.BitbucketAPIClient") as mock_api_client,
        ):
            # Setup mocks
            mock_storage.return_value.get_oauth_app.return_value = mock_oauth_app
            mock_storage.return_value.store_oauth_token.return_value = True
            mock_storage.return_value.get_storage_info.return_value = {"storage_type": "System keyring"}

            mock_manager.return_value.build_authorization_url.return_value = (
                "https://bitbucket.org/oauth/authorize?...",
                "code_verifier",
                "state",
            )
            mock_manager.return_value.exchange_code_for_token.return_value = mock_oauth_token

            # Mock server behavior
            mock_server_instance = Mock()
            mock_server_instance.callback_received = False
            mock_server_instance.authorization_code = "test_auth_code"
            mock_server_instance.state = "state"
            mock_server_instance.error = None
            mock_server.return_value = mock_server_instance

            # Mock API client
            mock_api_client.return_value.test_authentication.return_value = {
                "username": "testuser",
                "display_name": "Test User",
            }

            # Simulate server receiving callback
            def handle_request():
                mock_server_instance.callback_received = True

            mock_server_instance.handle_request = handle_request

            result = runner.invoke(auth, ["login", "--no-browser"], obj=mock_context)

            assert result.exit_code == 0
            assert "OAuth 2.0 authentication flow" in result.output
            assert "Authorization URL:" in result.output
            assert "OAuth 2.0 authentication successful!" in result.output

    def test_auth_login_oauth_error(self, runner, mock_context, mock_oauth_app):
        """Test auth login when OAuth returns an error."""
        with (
            patch("bbcli.cli.auth.OAuthStorage") as mock_storage,
            patch("bbcli.cli.auth.OAuthManager") as mock_manager,
            patch("bbcli.cli.auth.OAuthCallbackServer") as mock_server,
        ):
            # Setup mocks
            mock_storage.return_value.get_oauth_app.return_value = mock_oauth_app

            mock_manager.return_value.build_authorization_url.return_value = (
                "https://bitbucket.org/oauth/authorize?...",
                "code_verifier",
                "state",
            )

            # Mock server behavior with error
            mock_server_instance = Mock()
            mock_server_instance.callback_received = False
            mock_server_instance.authorization_code = None
            mock_server_instance.state = "state"
            mock_server_instance.error = "access_denied"
            mock_server.return_value = mock_server_instance

            # Simulate server receiving callback with error
            def handle_request():
                mock_server_instance.callback_received = True

            mock_server_instance.handle_request = handle_request

            result = runner.invoke(auth, ["login", "--no-browser"], obj=mock_context)

            assert result.exit_code == 1
            assert "OAuth authentication failed: access_denied" in result.output

    def test_auth_login_basic_command(self, runner, mock_context):
        """Test auth login-basic command."""
        with patch("bbcli.cli.auth._setup_basic_auth") as mock_basic_auth:
            result = runner.invoke(auth, ["login-basic"], obj=mock_context)

            assert result.exit_code == 0
            mock_basic_auth.assert_called_once()

    def test_auth_status_no_auth(self, runner, mock_context):
        """Test auth status when not authenticated."""
        with (
            patch("bbcli.cli.auth.AuthManager") as mock_auth_manager,
            patch("bbcli.cli.auth.OAuthStorage") as mock_oauth_storage,
        ):
            mock_auth_manager.return_value.has_credentials.return_value = False
            mock_oauth_storage.return_value.has_oauth_token.return_value = False

            result = runner.invoke(auth, ["status"], obj=mock_context)

            assert result.exit_code == 0
            assert "Not authenticated" in result.output
            assert "Run 'bbcli auth login' to authenticate with OAuth 2.0 (recommended)" in result.output

    def test_auth_status_with_oauth(self, runner, mock_context, mock_oauth_token):
        """Test auth status when authenticated with OAuth."""
        with (
            patch("bbcli.cli.auth.AuthManager") as mock_auth_manager,
            patch("bbcli.cli.auth.OAuthStorage") as mock_oauth_storage,
            patch("bbcli.cli.auth.get_api_client") as mock_get_api_client,
        ):
            mock_auth_manager.return_value.has_credentials.return_value = False
            mock_auth_manager.return_value._keyring_available = True
            mock_oauth_storage.return_value.has_oauth_token.return_value = True
            mock_oauth_storage.return_value.get_oauth_token.return_value = mock_oauth_token

            mock_api_client = Mock()
            mock_api_client.is_using_oauth.return_value = True
            mock_api_client.test_authentication.return_value = {
                "username": "testuser",
                "display_name": "Test User",
                "account_id": "123456",
            }
            mock_get_api_client.return_value = mock_api_client

            result = runner.invoke(auth, ["status"], obj=mock_context)

            assert result.exit_code == 0
            assert "Authenticated (OAuth 2.0)" in result.output

    def test_auth_status_with_basic_auth(self, runner, mock_context):
        """Test auth status when authenticated with Basic Auth."""
        with (
            patch("bbcli.cli.auth.AuthManager") as mock_auth_manager,
            patch("bbcli.cli.auth.OAuthStorage") as mock_oauth_storage,
            patch("bbcli.cli.auth.get_api_client") as mock_get_api_client,
        ):
            mock_auth_manager.return_value.has_credentials.return_value = True
            mock_auth_manager.return_value._keyring_available = True
            mock_oauth_storage.return_value.has_oauth_token.return_value = False

            mock_api_client = Mock()
            mock_api_client.is_using_oauth.return_value = False
            mock_api_client.test_authentication.return_value = {
                "username": "testuser",
                "display_name": "Test User",
                "account_id": "123456",
            }
            mock_get_api_client.return_value = mock_api_client

            result = runner.invoke(auth, ["status"], obj=mock_context)

            assert result.exit_code == 0
            assert "Authenticated (Basic Auth (App Password))" in result.output

    def test_auth_status_invalid_credentials(self, runner, mock_context):
        """Test auth status when credentials are invalid."""

        with (
            patch("bbcli.cli.auth.AuthManager") as mock_auth_manager,
            patch("bbcli.cli.auth.OAuthStorage") as mock_oauth_storage,
            patch("bbcli.cli.auth.get_api_client") as mock_get_api_client,
        ):
            mock_auth_manager.return_value.has_credentials.return_value = True
            mock_oauth_storage.return_value.has_oauth_token.return_value = False

            mock_api_client = Mock()
            mock_api_client.test_authentication.side_effect = AuthenticationError("Invalid credentials")
            mock_get_api_client.return_value = mock_api_client

            result = runner.invoke(auth, ["status"], obj=mock_context)

            assert result.exit_code == 0
            assert "Stored credentials are invalid or expired" in result.output
            assert "Run 'bbcli auth login' to re-authenticate with OAuth 2.0" in result.output

    def test_auth_logout(self, runner, mock_context):
        """Test auth logout command."""
        with patch("bbcli.cli.auth.AuthManager") as mock_auth_manager:
            mock_auth_manager.return_value.has_credentials.return_value = True
            mock_auth_manager.return_value.delete_credentials.return_value = True

            # Simulate user confirming logout
            result = runner.invoke(auth, ["logout"], input="y\n", obj=mock_context)

            assert result.exit_code == 0
            assert "Credentials removed successfully" in result.output

    def test_auth_logout_no_credentials(self, runner, mock_context):
        """Test auth logout when no credentials exist."""
        with patch("bbcli.cli.auth.AuthManager") as mock_auth_manager:
            mock_auth_manager.return_value.has_credentials.return_value = False

            result = runner.invoke(auth, ["logout"], obj=mock_context)

            assert result.exit_code == 0
            assert "No stored credentials found" in result.output

    def test_auth_logout_cancelled(self, runner, mock_context):
        """Test auth logout when user cancels."""
        with patch("bbcli.cli.auth.AuthManager") as mock_auth_manager:
            mock_auth_manager.return_value.has_credentials.return_value = True

            # Simulate user cancelling logout
            result = runner.invoke(auth, ["logout"], input="n\n", obj=mock_context)

            assert result.exit_code == 0
            assert "Logout cancelled" in result.output
