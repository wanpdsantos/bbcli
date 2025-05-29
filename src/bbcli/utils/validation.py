"""
Input validation utilities for bbcli.

This module provides functions for validating user inputs according to
Bitbucket API requirements and best practices.
"""

import re

from bbcli.core.exceptions import ValidationError


def validate_project_key(project_key: str) -> str:
    """
    Validate a Bitbucket project key.

    Args:
        project_key: The project key to validate

    Returns:
        The validated project key (uppercase)

    Raises:
        ValidationError: If the project key is invalid
    """
    if not project_key:
        raise ValidationError("Project key cannot be empty")

    # Convert to uppercase as per Bitbucket convention
    project_key = project_key.upper()

    # Check length (Bitbucket typically allows 2-10 characters)
    if len(project_key) < 2 or len(project_key) > 10:
        raise ValidationError(
            f"Project key '{project_key}' must be between 2 and 10 characters",
            suggestion="Use a shorter, descriptive key like 'PROJ' or 'MYAPP'",
        )

    # Check format (alphanumeric, typically uppercase)
    if not re.match(r"^[A-Z0-9]+$", project_key):
        raise ValidationError(
            f"Project key '{project_key}' must contain only uppercase letters and numbers",
            suggestion="Use only A-Z and 0-9 characters, e.g., 'PROJ1' or 'MYAPP'",
        )

    return project_key


def validate_repository_slug(repo_slug: str) -> str:
    """
    Validate a Bitbucket repository slug.

    Args:
        repo_slug: The repository slug to validate

    Returns:
        The validated repository slug (lowercase)

    Raises:
        ValidationError: If the repository slug is invalid
    """
    if not repo_slug:
        raise ValidationError("Repository slug cannot be empty")

    # Convert to lowercase as per Bitbucket convention
    repo_slug = repo_slug.lower()

    # Check length (Bitbucket allows up to 62 characters)
    if len(repo_slug) > 62:
        raise ValidationError(
            f"Repository slug '{repo_slug}' is too long (max 62 characters)",
            suggestion="Use a shorter, descriptive name",
        )

    # Check format (alphanumeric, hyphens, underscores)
    if not re.match(r"^[a-z0-9._-]+$", repo_slug):
        raise ValidationError(
            f"Repository slug '{repo_slug}' contains invalid characters",
            suggestion="Use only lowercase letters, numbers, hyphens, underscores, and dots",
        )

    # Cannot start or end with special characters
    if repo_slug.startswith((".", "-", "_")) or repo_slug.endswith((".", "-", "_")):
        raise ValidationError(
            f"Repository slug '{repo_slug}' cannot start or end with '.', '-', or '_'",
            suggestion="Start and end with alphanumeric characters",
        )

    return repo_slug


def validate_workspace_slug(workspace: str) -> str:
    """
    Validate a Bitbucket workspace slug or UUID.

    Args:
        workspace: The workspace slug or UUID to validate

    Returns:
        The validated workspace identifier

    Raises:
        ValidationError: If the workspace identifier is invalid
    """
    if not workspace:
        raise ValidationError("Workspace cannot be empty")

    # Check if it's a UUID format
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    if re.match(uuid_pattern, workspace.lower()):
        return workspace.lower()

    # Check if it's a UUID with braces
    uuid_braces_pattern = r"^\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}$"
    if re.match(uuid_braces_pattern, workspace.lower()):
        return workspace.lower()

    # Otherwise, treat as workspace slug
    workspace = workspace.lower()

    # Check format for workspace slug
    if not re.match(r"^[a-z0-9._-]+$", workspace):
        raise ValidationError(
            f"Workspace slug '{workspace}' contains invalid characters",
            suggestion="Use only lowercase letters, numbers, hyphens, underscores, and dots",
        )

    return workspace


def validate_email(email: str) -> str:
    """
    Validate an email address.

    Args:
        email: The email address to validate

    Returns:
        The validated email address

    Raises:
        ValidationError: If the email is invalid
    """
    if not email:
        raise ValidationError("Email address cannot be empty")

    # Basic email validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValidationError(
            f"'{email}' is not a valid email address",
            suggestion="Use a valid email format like 'user@example.com'",
        )

    return email.lower()


def validate_user_identifier(user_id: str) -> str:
    """
    Validate a user identifier (email or account ID).

    Args:
        user_id: The user identifier to validate

    Returns:
        The validated user identifier

    Raises:
        ValidationError: If the user identifier is invalid
    """
    if not user_id:
        raise ValidationError("User identifier cannot be empty")

    # Check if it's a UUID (account ID)
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    uuid_braces_pattern = r"^\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}$"

    if re.match(uuid_pattern, user_id.lower()) or re.match(uuid_braces_pattern, user_id.lower()):
        return user_id.lower()

    # Otherwise, validate as email
    return validate_email(user_id)


def validate_permission_level(permission: str) -> str:
    """
    Validate a repository permission level.

    Args:
        permission: The permission level to validate

    Returns:
        The validated permission level

    Raises:
        ValidationError: If the permission level is invalid
    """
    if not permission:
        raise ValidationError("Permission level cannot be empty")

    permission = permission.lower()
    valid_permissions = ["read", "write", "admin"]

    if permission not in valid_permissions:
        raise ValidationError(
            f"Invalid permission level '{permission}'",
            suggestion=f"Use one of: {', '.join(valid_permissions)}",
        )

    return permission


def validate_branch_name(branch_name: str) -> str:
    """
    Validate a Git branch name.

    Args:
        branch_name: The branch name to validate

    Returns:
        The validated branch name

    Raises:
        ValidationError: If the branch name is invalid
    """
    if not branch_name:
        raise ValidationError("Branch name cannot be empty")

    # Git branch name restrictions
    invalid_patterns = [
        r"\.\.",
        r"@\{",
        r"\\",
        r"\s",
        r"~",
        r"\^",
        r":",
        r"\?",
        r"\*",
        r"\[",
        r"\.lock$",
        r"^\.",
        r"/$",
        r"/\.",
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, branch_name):
            raise ValidationError(
                f"Branch name '{branch_name}' contains invalid characters or patterns",
                suggestion="Use alphanumeric characters, hyphens, and forward slashes",
            )

    return branch_name


def validate_non_empty_string(value: str, field_name: str) -> str:
    """
    Validate that a string is not empty.

    Args:
        value: The string to validate
        field_name: Name of the field for error messages

    Returns:
        The validated string (stripped)

    Raises:
        ValidationError: If the string is empty
    """
    if not value or not value.strip():
        raise ValidationError(f"{field_name} cannot be empty")

    return value.strip()
