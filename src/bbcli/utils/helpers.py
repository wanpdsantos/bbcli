"""
General utility functions for bbcli.

This module contains helper functions that are used across different parts
of the application.
"""

import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import click


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation of an action.

    Args:
        message: The confirmation message to display
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    return click.confirm(message, default=default)


def get_config_dir() -> Path:
    """
    Get the bbcli configuration directory.

    Returns:
        Path to the configuration directory
    """
    config_dir = Path.home() / ".bbcli"
    config_dir.mkdir(mode=0o700, exist_ok=True)
    return config_dir


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.

    Args:
        url: The URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        text: The string to truncate
        max_length: Maximum length of the result
        suffix: Suffix to add when truncating

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_size(size_bytes: int) -> str:
    """
    Format a size in bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float /= 1024.0
        i += 1

    return f"{size_float:.1f} {size_names[i]}"


def safe_get_nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary.

    Args:
        data: The dictionary to search
        keys: List of keys representing the path to the value
        default: Default value if key path doesn't exist

    Returns:
        The value at the key path or default
    """
    current = data
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError, IndexError):
        return default


def extract_repo_info_from_url(url: str) -> dict[str, str] | None:
    """
    Extract workspace and repository information from a Bitbucket URL.

    Args:
        url: Bitbucket repository URL

    Returns:
        Dictionary with 'workspace' and 'repo' keys, or None if invalid
    """
    import logging

    try:
        parsed = urlparse(url)
        if "bitbucket.org" not in parsed.netloc:
            return None

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2:
            return {
                "workspace": path_parts[0],
                "repo": path_parts[1].replace(".git", ""),
            }
    except Exception:
        logging.exception("Exception occurred while extracting repo info from URL")

    return None


def get_terminal_width() -> int:
    """
    Get the width of the terminal.

    Returns:
        Terminal width in characters
    """
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80  # Default fallback


def is_interactive() -> bool:
    """
    Check if the current session is interactive.

    Returns:
        True if interactive, False otherwise
    """
    return sys.stdin.isatty() and sys.stdout.isatty()


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """
    Return the singular or plural form of a word based on count.

    Args:
        count: The count to check
        singular: Singular form of the word
        plural: Plural form (defaults to singular + 's')

    Returns:
        Appropriate form of the word
    """
    if count == 1:
        return singular

    if plural is None:
        plural = singular + "s"

    return plural


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data, showing only the first few characters.

    Args:
        data: The sensitive data to mask
        visible_chars: Number of characters to show at the beginning

    Returns:
        Masked string
    """
    if len(data) <= visible_chars:
        return "*" * len(data)

    return data[:visible_chars] + "*" * (len(data) - visible_chars)


def create_table_data(items: list[dict[str, Any]], columns: list[str]) -> list[list[str]]:
    """
    Create table data from a list of dictionaries.

    Args:
        items: List of dictionaries containing the data
        columns: List of column names to extract

    Returns:
        List of rows, where each row is a list of string values
    """
    rows = []
    for item in items:
        row = []
        for column in columns:
            value = safe_get_nested(item, column.split("."), "")
            if isinstance(value, (dict, list)):
                value = str(value)
            row.append(str(value))
        rows.append(row)

    return rows
