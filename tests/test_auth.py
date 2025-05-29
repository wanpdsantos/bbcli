"""
Tests for authentication functionality.
"""

from unittest.mock import patch

import pytest

from bbcli.core.auth_manager import AuthManager
from bbcli.core.exceptions import AuthenticationError


class TestAuthManager:
    """Test cases for AuthManager class."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary configuration directory."""
        config_dir = tmp_path / ".bbcli"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def auth_manager(self, temp_config_dir):
        """Create an AuthManager instance with temporary config directory."""
        with patch("bbcli.core.auth_manager.get_config") as mock_config:
            mock_config.return_value.config_dir = temp_config_dir
            auth_manager = AuthManager()
            auth_manager.config_dir = temp_config_dir
            auth_manager.credentials_file = temp_config_dir / "credentials.enc"
            return auth_manager

    def test_keyring_availability_check(self, auth_manager):
        """Test keyring availability checking."""
        with (
            patch("keyring.set_password"),
            patch("keyring.get_password", return_value="test"),
            patch("keyring.delete_password"),
        ):
            assert auth_manager._check_keyring_availability() is True

        with patch("keyring.set_password", side_effect=Exception("No keyring")):
            assert auth_manager._check_keyring_availability() is False

    @patch("keyring.set_password")
    @patch("keyring.get_password")
    def test_store_credentials_keyring(self, mock_get, mock_set, auth_manager):
        """Test storing credentials using system keyring."""
        auth_manager._keyring_available = True

        auth_manager.store_credentials("testuser", "testpass")

        assert mock_set.call_count == 2
        mock_set.assert_any_call(AuthManager.SERVICE_NAME, AuthManager.USERNAME_KEY, "testuser")
        mock_set.assert_any_call(AuthManager.SERVICE_NAME, AuthManager.APP_SECRET_KEY, "testpass")

    @patch("keyring.get_password")
    def test_get_credentials_keyring(self, mock_get, auth_manager):
        """Test retrieving credentials from system keyring."""
        auth_manager._keyring_available = True
        mock_get.side_effect = ["testuser", "testpass"]

        credentials = auth_manager.get_credentials()

        assert credentials == ("testuser", "testpass")
        assert mock_get.call_count == 2

    @patch("keyring.delete_password")
    def test_delete_credentials_keyring(self, mock_delete, auth_manager):
        """Test deleting credentials from system keyring."""
        auth_manager._keyring_available = True

        result = auth_manager.delete_credentials()

        assert result is True
        assert mock_delete.call_count == 2

    @patch("getpass.getpass", return_value="masterpass")
    def test_store_credentials_encrypted_file(self, mock_getpass, auth_manager):
        """Test storing credentials in encrypted file."""
        auth_manager._keyring_available = False

        auth_manager.store_credentials("testuser", "testpass")

        assert auth_manager.credentials_file.exists()
        assert auth_manager.credentials_file.stat().st_mode & 0o777 == 0o600

    @patch("getpass.getpass", return_value="masterpass")
    def test_get_credentials_encrypted_file(self, mock_getpass, auth_manager):
        """Test retrieving credentials from encrypted file."""
        auth_manager._keyring_available = False

        # First store credentials
        auth_manager.store_credentials("testuser", "testpass")

        # Then retrieve them
        credentials = auth_manager.get_credentials()

        assert credentials == ("testuser", "testpass")

    @patch("getpass.getpass", return_value="wrongpass")
    def test_get_credentials_wrong_password(self, mock_getpass, auth_manager):
        """Test retrieving credentials with wrong master password."""
        auth_manager._keyring_available = False

        # Store with one password
        with patch("getpass.getpass", return_value="correctpass"):
            auth_manager.store_credentials("testuser", "testpass")

        # Try to retrieve with wrong password
        with pytest.raises(AuthenticationError):
            auth_manager.get_credentials()

    def test_has_credentials_true(self, auth_manager):
        """Test has_credentials returns True when credentials exist."""
        with patch.object(auth_manager, "get_credentials", return_value=("user", "pass")):
            assert auth_manager.has_credentials() is True

    def test_has_credentials_false(self, auth_manager):
        """Test has_credentials returns False when no credentials exist."""
        with patch.object(auth_manager, "get_credentials", return_value=None):
            assert auth_manager.has_credentials() is False
