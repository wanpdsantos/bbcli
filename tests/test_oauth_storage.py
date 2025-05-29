"""
Tests for OAuth storage functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bbcli.core.oauth_manager import OAuthApp, OAuthToken
from bbcli.core.oauth_storage import OAuthStorage


class TestOAuthStorage:
    """Test cases for OAuth storage functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def oauth_storage(self, temp_config_dir):
        """Create OAuth storage instance with temporary directory."""
        with patch("bbcli.core.oauth_storage.AuthManager") as mock_auth_manager:
            mock_auth_manager.return_value.config_dir = temp_config_dir
            mock_auth_manager.return_value._keyring_available = False
            storage = OAuthStorage()
            storage.config_dir = temp_config_dir
            storage.oauth_app_file = temp_config_dir / "oauth_app.enc"
            storage.oauth_token_file = temp_config_dir / "oauth_token.enc"
            yield storage

    @pytest.fixture
    def sample_oauth_app(self):
        """Sample OAuth app for testing."""
        return OAuthApp(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8080/callback",
        )

    @pytest.fixture
    def sample_oauth_token(self):
        """Sample OAuth token for testing."""
        return OAuthToken(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="repository",
        )

    def test_oauth_storage_initialization(self, temp_config_dir):
        """Test OAuth storage initialization."""
        with patch("bbcli.core.oauth_storage.AuthManager") as mock_auth_manager:
            mock_auth_manager.return_value.config_dir = temp_config_dir

            storage = OAuthStorage()

            assert storage.config_dir == temp_config_dir
            assert storage.oauth_app_file == temp_config_dir / "oauth_app.enc"
            assert storage.oauth_token_file == temp_config_dir / "oauth_token.enc"

    def test_store_oauth_app_with_keyring(self, oauth_storage, sample_oauth_app):
        """Test storing OAuth app with keyring."""
        oauth_storage.auth_manager._keyring_available = True

        with patch("keyring.set_password") as mock_set_password:
            result = oauth_storage.store_oauth_app(sample_oauth_app)

            assert result is True
            mock_set_password.assert_called_once()

            # Verify the stored data
            call_args = mock_set_password.call_args
            assert call_args[0][0] == "bbcli_oauth_app"
            assert call_args[0][1] == "default"

            stored_data = json.loads(call_args[0][2])
            assert stored_data["client_id"] == "test_client_id"
            assert stored_data["client_secret"] == "test_client_secret"

    def test_store_oauth_app_with_file_encryption(self, oauth_storage, sample_oauth_app):
        """Test storing OAuth app with file encryption."""
        oauth_storage.auth_manager._keyring_available = False
        oauth_storage.auth_manager._encrypt_data = Mock(return_value=b"encrypted_data")

        result = oauth_storage.store_oauth_app(sample_oauth_app)

        assert result is True
        oauth_storage.auth_manager._encrypt_data.assert_called_once()
        assert oauth_storage.oauth_app_file.exists()
        assert oauth_storage.oauth_app_file.read_bytes() == b"encrypted_data"

    def test_get_oauth_app_with_keyring(self, oauth_storage, sample_oauth_app):
        """Test retrieving OAuth app from keyring."""
        oauth_storage.auth_manager._keyring_available = True
        app_json = json.dumps(sample_oauth_app.to_dict())

        with patch("keyring.get_password", return_value=app_json):
            retrieved_app = oauth_storage.get_oauth_app()

            assert retrieved_app is not None
            assert retrieved_app.client_id == sample_oauth_app.client_id
            assert retrieved_app.client_secret == sample_oauth_app.client_secret
            assert retrieved_app.redirect_uri == sample_oauth_app.redirect_uri

    def test_get_oauth_app_with_file_decryption(self, oauth_storage, sample_oauth_app):
        """Test retrieving OAuth app from encrypted file."""
        oauth_storage.auth_manager._keyring_available = False
        app_json = json.dumps(sample_oauth_app.to_dict())
        oauth_storage.auth_manager._decrypt_data = Mock(return_value=app_json)

        # Create encrypted file
        oauth_storage.oauth_app_file.write_bytes(b"encrypted_data")

        retrieved_app = oauth_storage.get_oauth_app()

        assert retrieved_app is not None
        assert retrieved_app.client_id == sample_oauth_app.client_id
        oauth_storage.auth_manager._decrypt_data.assert_called_once_with(b"encrypted_data")

    def test_get_oauth_app_not_found(self, oauth_storage):
        """Test retrieving OAuth app when none exists."""
        oauth_storage.auth_manager._keyring_available = False

        retrieved_app = oauth_storage.get_oauth_app()

        assert retrieved_app is None

    def test_store_oauth_token_with_keyring(self, oauth_storage, sample_oauth_token):
        """Test storing OAuth token with keyring."""
        oauth_storage.auth_manager._keyring_available = True

        with patch("keyring.set_password") as mock_set_password:
            result = oauth_storage.store_oauth_token(sample_oauth_token)

            assert result is True
            mock_set_password.assert_called_once()

            # Verify the stored data
            call_args = mock_set_password.call_args
            assert call_args[0][0] == "bbcli_oauth_credentials"
            assert call_args[0][1] == "default"

            stored_data = json.loads(call_args[0][2])
            assert stored_data["access_token"] == "test_access_token"
            assert stored_data["token_type"] == "Bearer"

    def test_store_oauth_token_with_file_encryption(self, oauth_storage, sample_oauth_token):
        """Test storing OAuth token with file encryption."""
        oauth_storage.auth_manager._keyring_available = False
        oauth_storage.auth_manager._encrypt_data = Mock(return_value=b"encrypted_token_data")

        result = oauth_storage.store_oauth_token(sample_oauth_token)

        assert result is True
        oauth_storage.auth_manager._encrypt_data.assert_called_once()
        assert oauth_storage.oauth_token_file.exists()
        assert oauth_storage.oauth_token_file.read_bytes() == b"encrypted_token_data"

    def test_get_oauth_token_with_file_decryption(self, oauth_storage, sample_oauth_token):
        """Test retrieving OAuth token from encrypted file."""
        oauth_storage.auth_manager._keyring_available = False
        token_json = json.dumps(sample_oauth_token.to_dict())
        oauth_storage.auth_manager._decrypt_data = Mock(return_value=token_json)

        # Create encrypted file
        oauth_storage.oauth_token_file.write_bytes(b"encrypted_token_data")

        retrieved_token = oauth_storage.get_oauth_token()

        assert retrieved_token is not None
        assert retrieved_token.access_token == sample_oauth_token.access_token
        oauth_storage.auth_manager._decrypt_data.assert_called_once_with(b"encrypted_token_data")

    def test_has_oauth_app_true(self, oauth_storage, sample_oauth_app):
        """Test has_oauth_app returns True when app exists."""
        oauth_storage.get_oauth_app = Mock(return_value=sample_oauth_app)

        assert oauth_storage.has_oauth_app() is True

    def test_has_oauth_app_false(self, oauth_storage):
        """Test has_oauth_app returns False when app doesn't exist."""
        oauth_storage.get_oauth_app = Mock(return_value=None)

        assert oauth_storage.has_oauth_app() is False

    def test_has_oauth_token_true(self, oauth_storage, sample_oauth_token):
        """Test has_oauth_token returns True when token exists."""
        oauth_storage.get_oauth_token = Mock(return_value=sample_oauth_token)

        assert oauth_storage.has_oauth_token() is True

    def test_has_oauth_token_false(self, oauth_storage):
        """Test has_oauth_token returns False when token doesn't exist."""
        oauth_storage.get_oauth_token = Mock(return_value=None)

        assert oauth_storage.has_oauth_token() is False

    def test_get_valid_token_not_expired(self, oauth_storage):
        """Test get_valid_token returns token when not expired."""
        import time

        # Create a token that expires in the future
        valid_token = OAuthToken(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,  # 1 hour
            created_at=time.time(),  # Just created
        )
        oauth_storage.get_oauth_token = Mock(return_value=valid_token)

        result = oauth_storage.get_valid_token()

        assert result == valid_token

    def test_get_valid_token_expired(self, oauth_storage):
        """Test get_valid_token returns None when token is expired."""
        import time

        # Create a token that expired in the past
        expired_token = OAuthToken(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,  # 1 hour
            created_at=time.time() - 7200,  # Created 2 hours ago (expired)
        )
        oauth_storage.get_oauth_token = Mock(return_value=expired_token)

        result = oauth_storage.get_valid_token()

        assert result is None

    def test_delete_oauth_app_with_keyring(self, oauth_storage):
        """Test deleting OAuth app from keyring."""
        oauth_storage.auth_manager._keyring_available = True

        with patch("keyring.delete_password") as mock_delete_password:
            result = oauth_storage.delete_oauth_app()

            assert result is True
            mock_delete_password.assert_called_once_with("bbcli_oauth_app", "default")

    def test_delete_oauth_app_with_file(self, oauth_storage):
        """Test deleting OAuth app from encrypted file."""
        oauth_storage.auth_manager._keyring_available = False

        # Create file to delete
        oauth_storage.oauth_app_file.write_bytes(b"test_data")
        assert oauth_storage.oauth_app_file.exists()

        result = oauth_storage.delete_oauth_app()

        assert result is True
        assert not oauth_storage.oauth_app_file.exists()

    def test_clear_all_oauth_data(self, oauth_storage):
        """Test clearing all OAuth data."""
        oauth_storage.delete_oauth_app = Mock(return_value=True)
        oauth_storage.delete_oauth_token = Mock(return_value=True)

        result = oauth_storage.clear_all_oauth_data()

        assert result is True
        oauth_storage.delete_oauth_app.assert_called_once()
        oauth_storage.delete_oauth_token.assert_called_once()

    def test_get_storage_info(self, oauth_storage):
        """Test getting storage information."""
        oauth_storage.auth_manager._keyring_available = False
        oauth_storage.has_oauth_app = Mock(return_value=True)
        oauth_storage.has_oauth_token = Mock(return_value=False)

        info = oauth_storage.get_storage_info()

        assert info["storage_type"] == "Encrypted local file"
        assert info["has_oauth_app"] is True
        assert info["has_oauth_token"] is False
        assert "oauth_app_file" in info
        assert "oauth_token_file" in info
