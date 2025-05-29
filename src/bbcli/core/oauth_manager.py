"""
OAuth 2.0 manager for Bitbucket Cloud authentication.

This module handles OAuth 2.0 flows including Authorization Code Grant and Client Credentials Grant.
"""

import base64
import hashlib
import secrets
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any

import requests

from bbcli.core.config import get_config
from bbcli.core.exceptions import AuthenticationError


@dataclass
class OAuthToken:
    """OAuth 2.0 token information."""

    access_token: str
    token_type: str = "Bearer"  # OAuth 2.0 standard token type  # noqa: S105
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    created_at: float | None = None

    def __post_init__(self) -> None:
        """Set creation time if not provided."""
        if self.created_at is None:
            self.created_at = time.time()

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_in is None or self.created_at is None:
            return False

        return time.time() > (self.created_at + self.expires_in - 60)  # 60s buffer

    @property
    def expires_at(self) -> float | None:
        """Get the expiration timestamp."""
        if self.expires_in is None or self.created_at is None:
            return None
        return self.created_at + self.expires_in

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OAuthToken":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class OAuthApp:
    """OAuth 2.0 application credentials."""

    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8080/callback"
    scopes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "scopes": self.scopes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OAuthApp":
        """Create from dictionary."""
        return cls(**data)


class OAuthManager:
    """Manages OAuth 2.0 authentication flows for Bitbucket Cloud."""

    # Bitbucket OAuth 2.0 endpoints
    AUTHORIZE_URL = "https://bitbucket.org/site/oauth2/authorize"
    ACCESS_TOKEN_URL = "https://bitbucket.org/site/oauth2/access_token"  # noqa: S105

    # Default scopes for CLI application
    DEFAULT_SCOPES = [
        "account",
        "repository",
        "repository:write",
        "pullrequest",
        "pullrequest:write",
        "project",
        "webhook",
    ]

    def __init__(self) -> None:
        """Initialize OAuth manager."""
        self.config = get_config()
        self.session = requests.Session()

    def generate_pkce_pair(self) -> tuple[str, str]:
        """
        Generate PKCE code verifier and challenge for secure OAuth flow.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        )

        return code_verifier, code_challenge

    def build_authorization_url(
        self, oauth_app: OAuthApp, state: str | None = None, use_pkce: bool = True
    ) -> tuple[str, str | None, str | None]:
        """
        Build authorization URL for OAuth 2.0 Authorization Code flow.

        Args:
            oauth_app: OAuth application credentials
            state: Optional state parameter for CSRF protection
            use_pkce: Whether to use PKCE for additional security

        Returns:
            Tuple of (authorization_url, code_verifier, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": oauth_app.client_id,
            "response_type": "code",
            "redirect_uri": oauth_app.redirect_uri,
            "state": state,
        }

        if oauth_app.scopes:
            params["scope"] = oauth_app.scopes

        code_verifier = None
        if use_pkce:
            code_verifier, code_challenge = self.generate_pkce_pair()
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        auth_url = f"{self.AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
        return auth_url, code_verifier, state

    def exchange_code_for_token(
        self,
        oauth_app: OAuthApp,
        authorization_code: str,
        code_verifier: str | None = None,
    ) -> OAuthToken:
        """
        Exchange authorization code for access token.

        Args:
            oauth_app: OAuth application credentials
            authorization_code: Authorization code from callback
            code_verifier: PKCE code verifier if used

        Returns:
            OAuth token information

        Raises:
            AuthenticationError: If token exchange fails
        """
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": oauth_app.redirect_uri,
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        # Use Basic Auth with client credentials
        auth = (oauth_app.client_id, oauth_app.client_secret)

        try:
            response = self.session.post(
                self.ACCESS_TOKEN_URL,
                data=data,
                auth=auth,
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if not response.ok:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception as e:
                    error_msg = error_data.get("error_description", "Token exchange failed")
                    raise AuthenticationError(
                        f"OAuth token exchange failed: {error_msg}",
                        suggestion="Check your OAuth app configuration and try again",
                    ) from e

            token_data = response.json()
            return OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope"),
            )

        except Exception as e:
            raise AuthenticationError(
                f"Network error during token exchange: {e}",
                suggestion="Check your internet connection and try again",
            ) from e

    def refresh_access_token(self, oauth_app: OAuthApp, refresh_token: str) -> OAuthToken:
        """
        Refresh an expired access token.

        Args:
            oauth_app: OAuth application credentials
            refresh_token: Refresh token

        Returns:
            New OAuth token information

        Raises:
            AuthenticationError: If token refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        auth = (oauth_app.client_id, oauth_app.client_secret)

        try:
            response = self.session.post(
                self.ACCESS_TOKEN_URL,
                data=data,
                auth=auth,
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if not response.ok:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception as exc:
                    error_msg = error_data.get("error_description", "Token refresh failed")
                    raise AuthenticationError(
                        f"OAuth token refresh failed: {error_msg}",
                        suggestion="Please re-authenticate using 'bbcli auth login'",
                    ) from exc

            token_data = response.json()
            return OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_token=token_data.get("refresh_token", refresh_token),  # Keep old if not provided
                scope=token_data.get("scope"),
            )

        except Exception as e:
            raise AuthenticationError(
                f"Network error during token refresh: {e}",
                suggestion="Check your internet connection and try again",
            ) from e

    def client_credentials_flow(self, oauth_app: OAuthApp) -> OAuthToken:
        """
        Perform OAuth 2.0 Client Credentials flow.

        Args:
            oauth_app: OAuth application credentials

        Returns:
            OAuth token information

        Raises:
            AuthenticationError: If authentication fails
        """
        data = {
            "grant_type": "client_credentials",
        }

        if oauth_app.scopes:
            data["scope"] = oauth_app.scopes

        auth = (oauth_app.client_id, oauth_app.client_secret)

        try:
            response = self.session.post(
                self.ACCESS_TOKEN_URL,
                data=data,
                auth=auth,
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if not response.ok:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception as e:
                    error_msg = error_data.get("error_description", "Client credentials authentication failed")
                    raise AuthenticationError(
                        f"OAuth client credentials flow failed: {error_msg}",
                        suggestion="Check your OAuth app client ID and secret",
                    ) from e

            token_data = response.json()
            return OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                scope=token_data.get("scope"),
            )

        except Exception as e:
            raise AuthenticationError(
                f"Network error during client credentials flow: {e}",
                suggestion="Check your internet connection and try again",
            ) from e
