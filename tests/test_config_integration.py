"""
Tests for Config integration with other components.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from bbcli.core.config import Config, get_config


class TestConfigIntegration:
    """Test cases for Config integration with other bbcli components."""

    def setup_method(self):
        """Reset singleton before each test."""
        Config.reset_singleton()

    def teardown_method(self):
        """Clean up after each test."""
        Config.reset_singleton()

    def test_config_with_auth_manager(self):
        """Test that config works with AuthManager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "test_config"

            # Mock get_config to return our test config
            with patch("bbcli.core.auth_manager.get_config") as mock_get_config:
                test_config = Config(config_dir)
                mock_get_config.return_value = test_config

                # Import and create AuthManager
                from bbcli.core.auth_manager import AuthManager

                auth_manager = AuthManager()

                # Verify it uses the mocked config
                assert auth_manager.config is test_config
                assert auth_manager.config_dir == config_dir

    def test_config_with_api_client(self):
        """Test that config works with API client."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "test_config"

            # Create config with custom API settings
            config = Config(config_dir)
            config.set("api.timeout", 45)
            config.set("api.base_url", "https://custom.api.url")

            # Mock get_config to return our test config
            with patch("bbcli.core.api_client.get_config") as mock_get_config:
                mock_get_config.return_value = config

                # Import and test API client config usage
                from bbcli.core.api_client import BitbucketAPIClient

                # Create API client (this should use our config)
                api_client = BitbucketAPIClient()

                # Verify it got the config values
                mock_get_config.assert_called()

    def test_config_singleton_across_modules(self):
        """Test that singleton works across different modules."""
        # Set a value in config
        config1 = get_config()
        config1.set("test.cross_module", "shared_value")

        # Mock get_config calls to return the singleton
        with patch("bbcli.core.auth_manager.get_config", return_value=config1):
            with patch("bbcli.core.api_client.get_config", return_value=config1):
                # Import modules that use config
                from bbcli.core.auth_manager import AuthManager

                # Create instances
                auth_manager = AuthManager()

                # They should all have access to the same config
                assert auth_manager.config.get("test.cross_module") == "shared_value"

    def test_config_default_values_integration(self):
        """Test that default config values work with components."""
        config = get_config()

        # Test default API values
        assert config.get("api.base_url") == "https://api.bitbucket.org/2.0"
        assert config.get("api.timeout") == 30
        assert config.get("api.max_retries") == 3

        # Test default UI values
        assert config.get("ui.show_progress") is True
        assert config.get("ui.confirm_destructive") is True
        assert config.get("ui.color") is True

        # Test default output format
        assert config.get("default_output_format") == "text"

    def test_config_modification_persistence(self):
        """Test that config modifications persist across component usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "test_config"

            # Create config and modify values
            config = Config(config_dir)
            config.set("api.timeout", 60)
            config.set("ui.color", False)
            config.set("custom.setting", "test_value")

            # Reset singleton to simulate app restart
            Config.reset_singleton()

            # Create new config instance
            new_config = Config(config_dir)

            # Values should be loaded from file
            assert new_config.get("api.timeout") == 60
            assert new_config.get("ui.color") is False
            assert new_config.get("custom.setting") == "test_value"

    def test_config_error_handling(self):
        """Test config error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "test_config"
            config = Config(config_dir)

            # Test getting non-existent key with default
            assert config.get("non.existent.key", "default") == "default"
            assert config.get("non.existent.key") is None

            # Test deleting non-existent key
            assert config.delete("non.existent.key") is False

            # Test setting and getting nested keys
            config.set("level1.level2.level3", "deep_value")
            assert config.get("level1.level2.level3") == "deep_value"

    def test_config_thread_safety_with_components(self):
        """Test that config singleton is thread-safe when used by components."""
        import threading
        import time

        results = []
        errors = []

        def worker(worker_id):
            try:
                # Each worker gets config and modifies it
                config = get_config()

                # Set a worker-specific value
                key = f"worker.{worker_id}"
                value = f"value_{worker_id}"
                config.set(key, value)

                # Small delay
                time.sleep(0.01)

                # Read back the value
                read_value = config.get(key)
                results.append((worker_id, value, read_value))

                # Also test that it's the same instance
                config2 = Config()
                assert config is config2

            except Exception as e:
                errors.append((worker_id, e))

        # Create worker threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)

        # Start and wait for threads
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 5

        # All workers should have successfully set and read their values
        for worker_id, set_value, read_value in results:
            assert set_value == read_value

    def test_config_reset_functionality(self):
        """Test config reset functionality."""
        config = get_config()

        # Modify some values
        config.set("api.timeout", 120)
        config.set("custom.value", "test")

        # Verify changes
        assert config.get("api.timeout") == 120
        assert config.get("custom.value") == "test"

        # Reset to defaults
        config.reset()

        # Verify reset
        assert config.get("api.timeout") == 30  # Default value
        assert config.get("custom.value") is None  # Should be gone

    def test_config_all_values(self):
        """Test getting all config values."""
        config = get_config()

        # Get all values
        all_values = config.get_all()

        # Should be a dictionary
        assert isinstance(all_values, dict)

        # Should contain default keys
        assert "api" in all_values
        assert "ui" in all_values
        assert "default_output_format" in all_values

        # Should be a copy (modifying it shouldn't affect config)
        all_values["test_key"] = "test_value"
        assert config.get("test_key") is None
