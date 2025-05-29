"""
Tests for OAuth 2.0 manager functionality.
"""

import base64
import hashlib
import time
from unittest.mock import Mock, patch

import pytest

from bbcli.core.oauth_manager import OAuthApp, OAuthManager, OAuthToken


class TestOAuthToken:
    """Test cases for OAuthToken class."""

    def test_oauth_token_creation(self):
        """Test OAuth token creation."""
        token = OAuthToken(
            access_token="test_token",
            token_type="bearer",
            expires_in=3600,
            refresh_token="refresh_token",
            scope="repository",
        )

        assert token.access_token == "test_token"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "refresh_token"
        assert token.scope == "repository"
        assert token.created_at is not None

    def test_oauth_token_expiration(self):
        """Test OAuth token expiration logic."""
        # Create token that expires in 1 hour
        token = OAuthToken(access_token="test_token", expires_in=3600, created_at=time.time())

        assert not token.is_expired

        # Create expired token
        expired_token = OAuthToken(
            access_token="test_token",
            expires_in=3600,
            created_at=time.time() - 3700,  # Created over an hour ago
        )

        assert expired_token.is_expired

    def test_oauth_token_no_expiration(self):
        """Test OAuth token without expiration."""
        token = OAuthToken(access_token="test_token", expires_in=None)

        assert not token.is_expired
        assert token.expires_at is None

    def test_oauth_token_serialization(self):
        """Test OAuth token serialization."""
        token = OAuthToken(
            access_token="test_token",
            token_type="bearer",
            expires_in=3600,
            refresh_token="refresh_token",
            scope="repository",
            created_at=1234567890.0,
        )

        token_dict = token.to_dict()
        assert token_dict["access_token"] == "test_token"
        assert token_dict["token_type"] == "bearer"
        assert token_dict["expires_in"] == 3600
        assert token_dict["refresh_token"] == "refresh_token"
        assert token_dict["scope"] == "repository"
        assert token_dict["created_at"] == 1234567890.0

        # Test deserialization
        new_token = OAuthToken.from_dict(token_dict)
        assert new_token.access_token == token.access_token
        assert new_token.token_type == token.token_type
        assert new_token.expires_in == token.expires_in
        assert new_token.refresh_token == token.refresh_token
        assert new_token.scope == token.scope
        assert new_token.created_at == token.created_at


class TestOAuthApp:
    """Test cases for OAuthApp class."""

    def test_oauth_app_creation(self):
        """Test OAuth app creation."""
        app = OAuthApp(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8080/callback",
            scopes="repository account",
        )

        assert app.client_id == "test_client_id"
        assert app.client_secret == "test_client_secret"
        assert app.redirect_uri == "http://localhost:8080/callback"
        assert app.scopes == "repository account"

    def test_oauth_app_serialization(self):
        """Test OAuth app serialization."""
        app = OAuthApp(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8080/callback",
            scopes="repository account",
        )

        app_dict = app.to_dict()
        assert app_dict["client_id"] == "test_client_id"
        assert app_dict["client_secret"] == "test_client_secret"
        assert app_dict["redirect_uri"] == "http://localhost:8080/callback"
        assert app_dict["scopes"] == "repository account"

        # Test deserialization
        new_app = OAuthApp.from_dict(app_dict)
        assert new_app.client_id == app.client_id
        assert new_app.client_secret == app.client_secret
        assert new_app.redirect_uri == app.redirect_uri
        assert new_app.scopes == app.scopes


class TestOAuthManager:
    """Test cases for OAuthManager class."""

    @pytest.fixture
    def oauth_manager(self):
        """Create OAuth manager instance."""
        return OAuthManager()

    @pytest.fixture
    def oauth_app(self):
        """Create OAuth app instance."""
        return OAuthApp(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8080/callback",
            scopes="repository account",
        )

    def test_generate_pkce_pair(self, oauth_manager):
        """Test PKCE code verifier and challenge generation."""
        code_verifier, code_challenge = oauth_manager.generate_pkce_pair()

        # Verify code verifier format
        assert len(code_verifier) >= 43
        assert len(code_verifier) <= 128

        # Verify code challenge is correct SHA256 hash
        expected_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        )

        assert code_challenge == expected_challenge

    def test_build_authorization_url(self, oauth_manager, oauth_app):
        """Test authorization URL building."""
        auth_url, code_verifier, state = oauth_manager.build_authorization_url(oauth_app)

        assert auth_url.startswith(oauth_manager.AUTHORIZE_URL)
        assert "client_id=test_client_id" in auth_url
        assert "response_type=code" in auth_url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback" in auth_url
        assert "scope=repository+account" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url
        assert "state=" in auth_url

        assert code_verifier is not None
        assert state is not None

    def test_build_authorization_url_no_pkce(self, oauth_manager, oauth_app):
        """Test authorization URL building without PKCE."""
        auth_url, code_verifier, state = oauth_manager.build_authorization_url(oauth_app, use_pkce=False)

        assert auth_url.startswith(oauth_manager.AUTHORIZE_URL)
        assert "code_challenge=" not in auth_url
        assert code_verifier is None
        assert state is not None

    @patch("requests.Session.post")
    def test_exchange_code_for_token_success(self, mock_post, oauth_manager, oauth_app):
        """Test successful authorization code exchange."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "test_refresh_token",
            "scope": "repository account",
        }
        mock_post.return_value = mock_response

        token = oauth_manager.exchange_code_for_token(oauth_app, "test_auth_code", "test_code_verifier")

        assert token.access_token == "test_access_token"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "test_refresh_token"
        assert token.scope == "repository account"

        # Verify request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == oauth_manager.ACCESS_TOKEN_URL
        assert kwargs["auth"] == (oauth_app.client_id, oauth_app.client_secret)
        assert kwargs["data"]["grant_type"] == "authorization_code"
        assert kwargs["data"]["code"] == "test_auth_code"
        assert kwargs["data"]["code_verifier"] == "test_code_verifier"

    @patch("requests.Session.post")
    def test_refresh_access_token_success(self, mock_post, oauth_manager, oauth_app):
        """Test successful token refresh."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token",
        }
        mock_post.return_value = mock_response

        token = oauth_manager.refresh_access_token(oauth_app, "old_refresh_token")

        assert token.access_token == "new_access_token"
        assert token.refresh_token == "new_refresh_token"

        # Verify request was made correctly
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["data"]["grant_type"] == "refresh_token"
        assert kwargs["data"]["refresh_token"] == "old_refresh_token"

    @patch("requests.Session.post")
    def test_client_credentials_flow_success(self, mock_post, oauth_manager, oauth_app):
        """Test successful client credentials flow."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "access_token": "client_access_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "scope": "repository",
        }
        mock_post.return_value = mock_response

        token = oauth_manager.client_credentials_flow(oauth_app)

        assert token.access_token == "client_access_token"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600
        assert token.scope == "repository"

        # Verify request was made correctly
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["data"]["grant_type"] == "client_credentials"
