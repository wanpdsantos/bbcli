"""
Tests for AuthManager encryption methods used by OAuth storage.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from bbcli.core.auth_manager import AuthManager
from bbcli.core.exceptions import AuthenticationError


class TestAuthManagerEncryption:
    """Test cases for AuthManager encryption methods."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def auth_manager(self, temp_config_dir):
        """Create AuthManager instance with temporary directory."""
        with patch("bbcli.core.auth_manager.get_config") as mock_config:
            mock_config.return_value.config_dir = temp_config_dir
            manager = AuthManager()
            manager.config_dir = temp_config_dir
            manager.credentials_file = temp_config_dir / "credentials.enc"
            yield manager

    def test_encrypt_decrypt_data_roundtrip(self, auth_manager):
        """Test that data can be encrypted and then decrypted successfully."""
        test_data = '{"test": "data", "number": 123, "boolean": true}'

        # Mock getpass to provide consistent password
        with patch("getpass.getpass", side_effect=["test_password", "test_password"]):
            # Encrypt the data
            encrypted_data = auth_manager._encrypt_data(test_data)

            # Verify it's actually encrypted (different from original)
            assert encrypted_data != test_data.encode()
            assert isinstance(encrypted_data, bytes)

            # Decrypt the data
            decrypted_data = auth_manager._decrypt_data(encrypted_data)

            # Verify it matches the original
            assert decrypted_data == test_data

    def test_encrypt_data_different_passwords_different_results(self, auth_manager):
        """Test that different passwords produce different encrypted results."""
        test_data = '{"test": "data"}'

        # Encrypt with first password
        with patch("getpass.getpass", return_value="password1"):
            encrypted1 = auth_manager._encrypt_data(test_data)

        # Encrypt with second password
        with patch("getpass.getpass", return_value="password2"):
            encrypted2 = auth_manager._encrypt_data(test_data)

        # Results should be different
        assert encrypted1 != encrypted2

    def test_decrypt_data_wrong_password(self, auth_manager):
        """Test that decryption fails with wrong password."""
        test_data = '{"test": "data"}'

        # Encrypt with one password
        with patch("getpass.getpass", return_value="correct_password"):
            encrypted_data = auth_manager._encrypt_data(test_data)

        # Try to decrypt with wrong password
        with patch("getpass.getpass", return_value="wrong_password"):
            with pytest.raises(AuthenticationError) as exc_info:
                auth_manager._decrypt_data(encrypted_data)

            assert "Failed to decrypt stored data" in str(exc_info.value)
            # Check that the suggestion is present
            assert exc_info.value.suggestion == "Check your master password or re-authenticate"

    def test_decrypt_data_invalid_data(self, auth_manager):
        """Test that decryption fails with invalid encrypted data."""
        invalid_data = b"this is not valid encrypted data"

        with patch("getpass.getpass", return_value="any_password"):
            with pytest.raises(AuthenticationError) as exc_info:
                auth_manager._decrypt_data(invalid_data)

            assert "Failed to decrypt stored data" in str(exc_info.value)

    def test_encrypt_data_empty_string(self, auth_manager):
        """Test encrypting and decrypting empty string."""
        test_data = ""

        with patch("getpass.getpass", side_effect=["test_password", "test_password"]):
            encrypted_data = auth_manager._encrypt_data(test_data)
            decrypted_data = auth_manager._decrypt_data(encrypted_data)

            assert decrypted_data == test_data

    def test_encrypt_data_unicode_content(self, auth_manager):
        """Test encrypting and decrypting unicode content."""
        test_data = '{"message": "Hello 世界! 🌍", "emoji": "🔐"}'

        with patch("getpass.getpass", side_effect=["test_password", "test_password"]):
            encrypted_data = auth_manager._encrypt_data(test_data)
            decrypted_data = auth_manager._decrypt_data(encrypted_data)

            assert decrypted_data == test_data

    def test_encrypt_data_large_content(self, auth_manager):
        """Test encrypting and decrypting large content."""
        # Create a large JSON string
        large_data = '{"data": "' + "x" * 10000 + '"}'

        with patch("getpass.getpass", side_effect=["test_password", "test_password"]):
            encrypted_data = auth_manager._encrypt_data(large_data)
            decrypted_data = auth_manager._decrypt_data(encrypted_data)

            assert decrypted_data == large_data

    def test_encryption_key_generation_consistency(self, auth_manager):
        """Test that the same password generates the same encryption key."""
        password = "test_password"

        # Generate key twice with same password
        key1 = auth_manager._get_encryption_key(password)
        key2 = auth_manager._get_encryption_key(password)

        # Should be identical
        assert key1 == key2

    def test_encryption_key_generation_different_passwords(self, auth_manager):
        """Test that different passwords generate different encryption keys."""
        key1 = auth_manager._get_encryption_key("password1")
        key2 = auth_manager._get_encryption_key("password2")

        # Should be different
        assert key1 != key2

    def test_oauth_storage_integration(self, auth_manager):
        """Test that the encryption methods work with OAuth storage patterns."""
        import json

        # Simulate OAuth app data
        oauth_app_data = {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "redirect_uri": "http://localhost:8080/callback",
        }

        # Simulate OAuth token data
        oauth_token_data = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "test_refresh_token",
            "scope": "repository",
        }

        with patch("getpass.getpass", side_effect=["master_password"] * 4):
            # Encrypt OAuth app data
            app_json = json.dumps(oauth_app_data)
            encrypted_app = auth_manager._encrypt_data(app_json)

            # Encrypt OAuth token data
            token_json = json.dumps(oauth_token_data)
            encrypted_token = auth_manager._encrypt_data(token_json)

            # Decrypt OAuth app data
            decrypted_app_json = auth_manager._decrypt_data(encrypted_app)
            decrypted_app_data = json.loads(decrypted_app_json)

            # Decrypt OAuth token data
            decrypted_token_json = auth_manager._decrypt_data(encrypted_token)
            decrypted_token_data = json.loads(decrypted_token_json)

            # Verify data integrity
            assert decrypted_app_data == oauth_app_data
            assert decrypted_token_data == oauth_token_data

    def test_backward_compatibility_with_credentials(self, auth_manager):
        """Test that new encryption methods don't interfere with existing credential methods."""
        # Test that existing credential encryption still works
        username = "test_user"
        password = "test_password"

        with patch("getpass.getpass", side_effect=["master_password"] * 2):
            # Store credentials using existing method (this writes to file)
            encrypted_data = auth_manager._encrypt_credentials(username, password)

            # Write to file manually since _encrypt_credentials doesn't do it
            with open(auth_manager.credentials_file, "wb") as f:
                f.write(encrypted_data)

            # Retrieve credentials using existing method
            retrieved_creds = auth_manager._decrypt_credentials()

            assert retrieved_creds == (username, password)

    def test_encryption_methods_are_independent(self, auth_manager):
        """Test that generic encryption and credential encryption are independent."""
        # Store some generic data
        test_data = '{"generic": "data"}'

        # Store credentials
        username = "test_user"
        app_password = "test_app_password"

        with patch("getpass.getpass", side_effect=["master_password"] * 4):
            # Encrypt generic data
            encrypted_data = auth_manager._encrypt_data(test_data)

            # Store credentials (encrypt and write to file)
            encrypted_creds = auth_manager._encrypt_credentials(username, app_password)
            with open(auth_manager.credentials_file, "wb") as f:
                f.write(encrypted_creds)

            # Retrieve both
            decrypted_data = auth_manager._decrypt_data(encrypted_data)
            retrieved_creds = auth_manager._decrypt_credentials()

            # Both should work correctly
            assert decrypted_data == test_data
            assert retrieved_creds == (username, app_password)
