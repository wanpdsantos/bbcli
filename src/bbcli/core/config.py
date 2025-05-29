"""
Configuration management for bbcli.

This module handles loading and saving configuration settings,
including user preferences and default values.
"""

import os
import threading
from pathlib import Path
from typing import Any

import yaml

from bbcli.core.exceptions import ConfigurationError


class SingletonMeta(type):
    """
    Thread-safe singleton metaclass.

    This metaclass ensures that only one instance of a class can exist,
    even in multi-threaded environments.
    """

    _instances: dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs) -> Any:
        """Create or return the singleton instance."""
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class Config(metaclass=SingletonMeta):
    """Configuration manager for bbcli."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Initialize the configuration manager.

        Args:
            config_dir: Custom configuration directory path.
                       Defaults to ~/.bbcli/

        Note: Due to singleton pattern, this will only be called once.
              Subsequent calls will return the existing instance.
        """
        # Prevent re-initialization of singleton
        if hasattr(self, "_initialized"):
            return

        if config_dir is None:
            config_dir = Path.home() / ".bbcli"

        self.config_dir = config_dir
        self.config_file = config_dir / "config.yaml"
        self._config: dict[str, Any] = {}

        # Ensure config directory exists
        self.config_dir.mkdir(mode=0o700, exist_ok=True)

        # Load existing configuration
        self._load_config()

        # Mark as initialized
        self._initialized = True

    def _load_config(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except (yaml.YAMLError, OSError) as e:
                raise ConfigurationError(
                    f"Failed to load configuration file: {e}",
                    suggestion=f"Check that {self.config_file} is valid YAML",
                ) from e
        else:
            # Initialize with default configuration
            self._config = self._get_default_config()
            self._save_config()

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(self._config, f, default_flow_style=False)

            # Ensure config file has secure permissions
            os.chmod(self.config_file, 0o600)
        except OSError as e:
            raise ConfigurationError(
                f"Failed to save configuration file: {e}",
                suggestion=f"Check that {self.config_dir} is writable",
            ) from e

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration values."""
        return {
            "default_workspace": None,
            "default_output_format": "text",
            "api": {
                "base_url": "https://api.bitbucket.org/2.0",
                "timeout": 30,
                "max_retries": 3,
            },
            "ui": {
                "show_progress": True,
                "confirm_destructive": True,
                "color": True,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation, e.g., 'api.timeout')
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value

        # Save to file
        self._save_config()

    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key to delete

        Returns:
            True if key was deleted, False if it didn't exist
        """
        keys = key.split(".")
        config = self._config

        try:
            # Navigate to the parent of the target key
            for k in keys[:-1]:
                config = config[k]

            # Delete the key
            if keys[-1] in config:
                del config[keys[-1]]
                self._save_config()
                return True
            return False
        except (KeyError, TypeError):
            return False

    def get_all(self) -> dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = self._get_default_config()
        self._save_config()

    @classmethod
    def reset_singleton(cls) -> None:
        """
        Reset the singleton instance.

        This is primarily useful for testing purposes.
        """
        with SingletonMeta._lock:
            if cls in SingletonMeta._instances:
                del SingletonMeta._instances[cls]

    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if the singleton instance has been created.

        Returns:
            True if the singleton instance exists, False otherwise
        """
        return cls in SingletonMeta._instances


def get_config() -> Config:
    """
    Get the singleton configuration instance.

    Returns:
        The singleton Config instance
    """
    return Config()
