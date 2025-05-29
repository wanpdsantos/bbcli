"""
Tests for Config singleton implementation.
"""

import tempfile
import threading
import time
from pathlib import Path

from bbcli.core.config import Config, get_config


class TestConfigSingleton:
    """Test cases for Config singleton pattern."""

    def setup_method(self):
        """Reset singleton before each test."""
        Config.reset_singleton()

    def teardown_method(self):
        """Clean up after each test."""
        Config.reset_singleton()

    def test_singleton_same_instance(self):
        """Test that multiple calls return the same instance."""
        config1 = Config()
        config2 = Config()
        config3 = get_config()

        assert config1 is config2
        assert config2 is config3
        assert id(config1) == id(config2) == id(config3)

    def test_singleton_initialization_once(self):
        """Test that initialization only happens once."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "test_config"

            # First call should initialize
            config1 = Config(config_dir)
            assert config1.config_dir == config_dir

            # Second call should return same instance, ignore new config_dir
            different_dir = Path(temp_dir) / "different_config"
            config2 = Config(different_dir)

            assert config1 is config2
            assert config2.config_dir == config_dir  # Should still be original
            assert config2.config_dir != different_dir

    def test_singleton_thread_safety(self):
        """Test that singleton is thread-safe."""
        instances = []
        errors = []

        def create_config():
            try:
                config = Config()
                instances.append(config)
            except Exception as e:
                errors.append(e)

        # Create multiple threads that try to create config instances
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_config)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(instances) == 10

        # All instances should be the same object
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance

    def test_singleton_reset(self):
        """Test that singleton can be reset."""
        # Create first instance
        config1 = Config()
        config1_id = id(config1)

        # Reset singleton
        Config.reset_singleton()

        # Create new instance
        config2 = Config()
        config2_id = id(config2)

        # Should be different instances
        assert config1_id != config2_id
        assert config1 is not config2

    def test_singleton_is_initialized(self):
        """Test is_initialized class method."""
        # Initially not initialized
        assert not Config.is_initialized()

        # Create instance
        _ = Config()
        assert Config.is_initialized()

        # Reset and check again
        Config.reset_singleton()
        assert not Config.is_initialized()

    def test_get_config_function(self):
        """Test that get_config() returns singleton instance."""
        config1 = get_config()
        config2 = get_config()
        direct_config = Config()

        assert config1 is config2
        assert config1 is direct_config

    def test_singleton_with_custom_config_dir(self):
        """Test singleton with custom configuration directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir) / "custom_bbcli"

            config = Config(custom_dir)

            assert config.config_dir == custom_dir
            assert config.config_file == custom_dir / "config.yaml"
            assert custom_dir.exists()

    def test_singleton_preserves_state(self):
        """Test that singleton preserves state across calls."""
        # Create config and set a value
        config1 = Config()
        config1.set("test.key", "test_value")

        # Get config again and check value is preserved
        config2 = Config()
        assert config2.get("test.key") == "test_value"

        # Use get_config function
        config3 = get_config()
        assert config3.get("test.key") == "test_value"

    def test_singleton_configuration_persistence(self):
        """Test that configuration changes persist across singleton calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "test_config"

            # Create config and modify it
            config1 = Config(config_dir)
            config1.set("api.timeout", 60)
            config1.set("ui.color", False)

            # Reset singleton (simulating app restart)
            Config.reset_singleton()

            # Create new instance with same config dir
            config2 = Config(config_dir)

            # Values should be loaded from file
            assert config2.get("api.timeout") == 60
            assert config2.get("ui.color") is False

    def test_singleton_default_values(self):
        """Test that singleton has correct default values."""
        config = Config()

        # Check default values
        assert config.get("default_workspace") is None
        assert config.get("default_output_format") == "text"
        assert config.get("api.base_url") == "https://api.bitbucket.org/2.0"
        assert config.get("api.timeout") == 30
        assert config.get("api.max_retries") == 3
        assert config.get("ui.show_progress") is True
        assert config.get("ui.confirm_destructive") is True
        assert config.get("ui.color") is True

    def test_singleton_concurrent_access(self):
        """Test concurrent access to singleton configuration."""
        results = []
        errors = []

        def worker(worker_id):
            try:
                # Each worker gets the same config instance
                worker_config = Config()

                # Set a value specific to this worker
                key = f"worker.{worker_id}"
                value = f"value_{worker_id}"
                worker_config.set(key, value)

                # Small delay to allow other workers to run
                time.sleep(0.01)

                # Read back the value
                read_value = worker_config.get(key)
                results.append((worker_id, value, read_value))

            except Exception as e:
                errors.append((worker_id, e))

        # Create multiple worker threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 5

        # All workers should have successfully set and read their values
        for worker_id, set_value, read_value in results:
            assert set_value == read_value == f"value_{worker_id}"

    def test_singleton_memory_efficiency(self):
        """Test that singleton doesn't create multiple instances."""
        import gc

        # Create multiple references
        configs = []
        for _ in range(100):
            configs.append(Config())

        # All should be the same object
        first_config = configs[0]
        for config in configs[1:]:
            assert config is first_config

        # Clear references and force garbage collection
        configs.clear()
        gc.collect()

        # Create new config - should still be the same instance
        new_config = Config()
        assert new_config is first_config

    def test_singleton_with_get_config_mixed_usage(self):
        """Test mixing direct Config() calls with get_config() calls."""
        # Mix different ways of getting config
        config1 = Config()
        config2 = get_config()
        config3 = Config()
        config4 = get_config()

        # All should be the same instance
        assert config1 is config2 is config3 is config4

        # State should be shared
        config1.set("mixed.test", "shared_value")
        assert config2.get("mixed.test") == "shared_value"
        assert config3.get("mixed.test") == "shared_value"
        assert config4.get("mixed.test") == "shared_value"
