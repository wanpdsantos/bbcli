"""
Authentication and credential management for bbcli.

This module handles secure storage and retrieval of Bitbucket credentials
using the system keyring or encrypted local storage as fallback.
"""

import base64
import getpass
import json
import os
from pathlib import Path

import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from rich.console import Console

from bbcli.core.config import get_config
from bbcli.core.exceptions import AuthenticationError, ConfigurationError
from bbcli.utils.output import OutputFormatter


class AuthManager:
    """Manages authentication credentials for bbcli."""

    SERVICE_NAME = "bbcli"
    USERNAME_KEY = "bitbucket_username"
    APP_SECRET_KEY = "bitbucket_app_secret"  # noqa: S105

    def __init__(self) -> None:
        """Initialize the authentication manager."""
        self.config = get_config()
        self.config_dir = Path(self.config.config_dir)
        self.credentials_file = self.config_dir / "credentials.enc"

        # Check if system keyring is available
        self._keyring_available = self._check_keyring_availability()

    def _check_keyring_availability(self) -> bool:
        """Check if system keyring is available and functional."""
        try:
            # Test keyring functionality
            test_key = f"{self.SERVICE_NAME}_test"
            keyring.set_password(self.SERVICE_NAME, test_key, "test")
            retrieved = keyring.get_password(self.SERVICE_NAME, test_key)
            keyring.delete_password(self.SERVICE_NAME, test_key)
            return bool(retrieved == "test")
        except Exception:
            return False

    def _get_encryption_key(self, password: str) -> bytes:
        """Derive encryption key from password."""
        password_bytes = password.encode()
        salt = b"bbcli_salt_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key

    def _encrypt_credentials(self, username: str, app_password: str) -> bytes:
        """Encrypt credentials for local storage."""
        # Use a simple password for encryption (in production, consider better key derivation)
        master_password = getpass.getpass("Enter a master password to encrypt your credentials: ")
        key = self._get_encryption_key(master_password)

        fernet = Fernet(key)
        credentials = {"username": username, "app_password": app_password}

        encrypted_data: bytes = fernet.encrypt(json.dumps(credentials).encode())
        return encrypted_data

    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt arbitrary data for local storage."""
        # Use a simple password for encryption (in production, consider better key derivation)
        master_password = getpass.getpass("Enter a master password to encrypt your data: ")
        key = self._get_encryption_key(master_password)

        fernet = Fernet(key)
        encrypted_data: bytes = fernet.encrypt(data.encode())
        return encrypted_data

    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt arbitrary data from local storage."""
        try:
            master_password = getpass.getpass("Enter your master password: ")
            key = self._get_encryption_key(master_password)

            fernet = Fernet(key)
            decrypted_data: bytes = fernet.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            raise AuthenticationError(
                f"Failed to decrypt stored data: {e}",
                suggestion="Check your master password or re-authenticate",
            ) from e

    def _decrypt_credentials(self) -> tuple[str, str] | None:
        """Decrypt credentials from local storage."""
        if not self.credentials_file.exists():
            return None

        try:
            master_password = getpass.getpass("Enter your master password: ")
            key = self._get_encryption_key(master_password)

            fernet = Fernet(key)

            with open(self.credentials_file, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())

            return credentials["username"], credentials["app_password"]
        except Exception as e:
            raise AuthenticationError(
                f"Failed to decrypt stored credentials: {e}",
                suggestion="Try running 'bbcli auth login' to re-authenticate",
            ) from e

    def store_credentials(self, username: str, app_password: str) -> None:
        """
        Store credentials securely.

        Args:
            username: Bitbucket username
            app_password: Bitbucket app password
        """
        if self._keyring_available:
            try:
                keyring.set_password(self.SERVICE_NAME, self.USERNAME_KEY, username)
                keyring.set_password(self.SERVICE_NAME, self.APP_SECRET_KEY, app_password)

                # Remove encrypted file if it exists (migrating from fallback)
                if self.credentials_file.exists():
                    self.credentials_file.unlink()

                return
            except Exception as e:
                OutputFormatter("text", Console()).warning(f"Failed to store credentials in system keyring: {e}")
                OutputFormatter("text", Console()).warning("Falling back to encrypted local storage...")

        # Fallback to encrypted local storage
        try:
            encrypted_data = self._encrypt_credentials(username, app_password)

            with open(self.credentials_file, "wb") as f:
                f.write(encrypted_data)

            # Secure file permissions
            os.chmod(self.credentials_file, 0o600)

            OutputFormatter("text", Console()).warning("For better security, consider setting up a system keyring.")

        except Exception as e:
            raise ConfigurationError(
                f"Failed to store credentials: {e}",
                suggestion="Check that the configuration directory is writable",
            ) from e

    def get_credentials(self) -> tuple[str, str] | None:
        """
        Retrieve stored credentials.

        Returns:
            Tuple of (username, app_password) or None if not found
        """
        # Try system keyring first
        if self._keyring_available:
            try:
                username = keyring.get_password(self.SERVICE_NAME, self.USERNAME_KEY)
                app_password = keyring.get_password(self.SERVICE_NAME, self.APP_SECRET_KEY)

                if username and app_password:
                    return username, app_password
            except Exception:
                import logging

                logging.exception("Exception occurred while retrieving credentials from keyring")

        # Try encrypted local storage
        return self._decrypt_credentials()

    def delete_credentials(self) -> bool:
        """
        Delete stored credentials.

        Returns:
            True if credentials were deleted, False if none were found
        """
        deleted = False

        # Delete from system keyring
        if self._keyring_available:
            try:
                keyring.delete_password(self.SERVICE_NAME, self.USERNAME_KEY)
                keyring.delete_password(self.SERVICE_NAME, self.APP_SECRET_KEY)
                deleted = True
            except keyring.errors.PasswordDeleteError:
                pass
            except Exception:
                import logging

                logging.exception("Exception occurred while deleting credentials from keyring")

        # Delete encrypted local file
        if self.credentials_file.exists():
            self.credentials_file.unlink()
            deleted = True

        return deleted

    def has_credentials(self) -> bool:
        """Check if credentials are stored."""
        return self.get_credentials() is not None
