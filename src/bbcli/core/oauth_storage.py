"""
OAuth 2.0 storage manager for secure token and app credential storage.

This module handles secure storage and retrieval of OAuth tokens and app credentials
using the same encryption and keyring mechanisms as the existing auth manager.
"""

import json

from bbcli.core.auth_manager import AuthManager
from bbcli.core.oauth_manager import OAuthApp, OAuthToken

BBCLI_OAUTH_APP = "bbcli_oauth_app"
BBCLI_OAUTH_CREDENTIALS = "bbcli_oauth_credentials"


class OAuthStorage:
    """Manages secure storage of OAuth 2.0 tokens and app credentials."""

    def __init__(self):
        """Initialize OAuth storage using existing auth manager infrastructure."""
        self.auth_manager = AuthManager()
        self.config_dir = self.auth_manager.config_dir

        # OAuth-specific storage files
        self.oauth_app_file = self.config_dir / "oauth_app.enc"
        self.oauth_token_file = self.config_dir / "oauth_token.enc"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def store_oauth_app(self, oauth_app: OAuthApp) -> bool:
        """
        Store OAuth app credentials securely.

        Args:
            oauth_app: OAuth application credentials

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            app_data = oauth_app.to_dict()
            app_json = json.dumps(app_data)

            if self.auth_manager._keyring_available:
                # Store in system keyring
                import keyring

                keyring.set_password(BBCLI_OAUTH_APP, "default", app_json)
            else:
                # Store in encrypted file
                encrypted_data = self.auth_manager._encrypt_data(app_json)
                self.oauth_app_file.write_bytes(encrypted_data)

            return True

        except Exception:
            return False

    def get_oauth_app(self) -> OAuthApp | None:
        """
        Retrieve OAuth app credentials.

        Returns:
            OAuth app credentials or None if not found
        """
        try:
            app_json = None

            if self.auth_manager._keyring_available:
                # Retrieve from system keyring
                import keyring

                app_json = keyring.get_password(BBCLI_OAUTH_APP, "default")
            else:
                # Retrieve from encrypted file
                if self.oauth_app_file.exists():
                    encrypted_data = self.oauth_app_file.read_bytes()
                    app_json = self.auth_manager._decrypt_data(encrypted_data)

            if app_json:
                app_data = json.loads(app_json)
                return OAuthApp.from_dict(app_data)

            return None

        except Exception:
            return None

    def delete_oauth_app(self) -> bool:
        """
        Delete stored OAuth app credentials.

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if self.auth_manager._keyring_available:
                # Delete from system keyring
                import keyring

                keyring.delete_password(BBCLI_OAUTH_APP, "default")
            else:
                # Delete encrypted file
                if self.oauth_app_file.exists():
                    self.oauth_app_file.unlink()

            return True

        except Exception:
            return False

    def has_oauth_app(self) -> bool:
        """
        Check if OAuth app credentials are stored.

        Returns:
            True if credentials exist, False otherwise
        """
        return self.get_oauth_app() is not None

    def store_oauth_token(self, oauth_token: OAuthToken) -> bool:
        """
        Store OAuth token securely.

        Args:
            oauth_token: OAuth token information

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            token_data = oauth_token.to_dict()
            token_json = json.dumps(token_data)

            if self.auth_manager._keyring_available:
                # Store in system keyring
                import keyring

                keyring.set_password(BBCLI_OAUTH_CREDENTIALS, "default", token_json)
            else:
                # Store in encrypted file
                encrypted_data = self.auth_manager._encrypt_data(token_json)
                self.oauth_token_file.write_bytes(encrypted_data)

            return True

        except Exception:
            return False

    def get_oauth_token(self) -> OAuthToken | None:
        """
        Retrieve OAuth token.

        Returns:
            OAuth token or None if not found
        """
        try:
            token_json = None

            if self.auth_manager._keyring_available:
                # Retrieve from system keyring
                import keyring

                token_json = keyring.get_password(BBCLI_OAUTH_CREDENTIALS, "default")
            else:
                # Retrieve from encrypted file
                if self.oauth_token_file.exists():
                    encrypted_data = self.oauth_token_file.read_bytes()
                    token_json = self.auth_manager._decrypt_data(encrypted_data)

            if token_json:
                token_data = json.loads(token_json)
                return OAuthToken.from_dict(token_data)

            return None

        except Exception:
            return None

    def delete_oauth_token(self) -> bool:
        """
        Delete stored OAuth token.

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if self.auth_manager._keyring_available:
                # Delete from system keyring
                import keyring

                keyring.delete_password(BBCLI_OAUTH_CREDENTIALS, "default")
            else:
                # Delete encrypted file
                if self.oauth_token_file.exists():
                    self.oauth_token_file.unlink()

            return True

        except Exception:
            return False

    def has_oauth_token(self) -> bool:
        """
        Check if OAuth token is stored.

        Returns:
            True if token exists, False otherwise
        """
        return self.get_oauth_token() is not None

    def get_valid_token(self) -> OAuthToken | None:
        """
        Get a valid (non-expired) OAuth token.

        Returns:
            Valid OAuth token or None if not available or expired
        """
        token = self.get_oauth_token()
        if token and not token.is_expired:
            return token
        return None

    def clear_all_oauth_data(self) -> bool:
        """
        Clear all stored OAuth data (app credentials and tokens).

        Returns:
            True if all data cleared successfully, False otherwise
        """
        app_deleted = self.delete_oauth_app()
        token_deleted = self.delete_oauth_token()
        return app_deleted and token_deleted

    def has_any_oauth_data(self) -> bool:
        """
        Check if any OAuth data is stored.

        Returns:
            True if any OAuth data exists, False otherwise
        """
        return self.has_oauth_app() or self.has_oauth_token()

    def get_storage_info(self) -> dict:
        """
        Get information about OAuth storage.

        Returns:
            Dictionary with storage information
        """
        return {
            "storage_type": ("System keyring" if self.auth_manager._keyring_available else "Encrypted local file"),
            "config_dir": str(self.config_dir),
            "has_oauth_app": self.has_oauth_app(),
            "has_oauth_token": self.has_oauth_token(),
            "oauth_app_file": (str(self.oauth_app_file) if not self.auth_manager._keyring_available else None),
            "oauth_token_file": (str(self.oauth_token_file) if not self.auth_manager._keyring_available else None),
        }
