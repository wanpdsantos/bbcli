"""
Tests for validation utilities.
"""

import pytest

from bbcli.core.exceptions import ValidationError
from bbcli.utils.validation import (
    validate_branch_name,
    validate_email,
    validate_non_empty_string,
    validate_permission_level,
    validate_project_key,
    validate_repository_slug,
    validate_user_identifier,
    validate_workspace_slug,
)


class TestValidation:
    """Test cases for validation functions."""

    def test_validate_project_key_valid(self):
        """Test valid project keys."""
        assert validate_project_key("PROJ") == "PROJ"
        assert validate_project_key("proj") == "PROJ"  # Should convert to uppercase
        assert validate_project_key("MYAPP123") == "MYAPP123"
        assert validate_project_key("AB") == "AB"  # Minimum length
        assert validate_project_key("ABCDEFGHIJ") == "ABCDEFGHIJ"  # Maximum length

    def test_validate_project_key_invalid(self):
        """Test invalid project keys."""
        with pytest.raises(ValidationError):
            validate_project_key("")  # Empty

        with pytest.raises(ValidationError):
            validate_project_key("A")  # Too short

        with pytest.raises(ValidationError):
            validate_project_key("ABCDEFGHIJK")  # Too long

        with pytest.raises(ValidationError):
            validate_project_key("PROJ-1")  # Contains hyphen

        with pytest.raises(ValidationError):
            validate_project_key("PROJ_1")  # Contains underscore

        with pytest.raises(ValidationError):
            validate_project_key("PROJ 1")  # Contains space

    def test_validate_repository_slug_valid(self):
        """Test valid repository slugs."""
        assert validate_repository_slug("my-repo") == "my-repo"
        assert validate_repository_slug("MY-REPO") == "my-repo"  # Should convert to lowercase
        assert validate_repository_slug("repo123") == "repo123"
        assert validate_repository_slug("my_repo") == "my_repo"
        assert validate_repository_slug("my.repo") == "my.repo"
        assert validate_repository_slug("repo-with-many-hyphens") == "repo-with-many-hyphens"

    def test_validate_repository_slug_invalid(self):
        """Test invalid repository slugs."""
        with pytest.raises(ValidationError):
            validate_repository_slug("")  # Empty

        with pytest.raises(ValidationError):
            validate_repository_slug("a" * 63)  # Too long

        with pytest.raises(ValidationError):
            validate_repository_slug(".repo")  # Starts with dot

        with pytest.raises(ValidationError):
            validate_repository_slug("repo.")  # Ends with dot

        with pytest.raises(ValidationError):
            validate_repository_slug("-repo")  # Starts with hyphen

        with pytest.raises(ValidationError):
            validate_repository_slug("repo-")  # Ends with hyphen

        with pytest.raises(ValidationError):
            validate_repository_slug("repo with spaces")  # Contains spaces

    def test_validate_workspace_slug_valid(self):
        """Test valid workspace slugs."""
        assert validate_workspace_slug("myworkspace") == "myworkspace"
        assert validate_workspace_slug("MYWORKSPACE") == "myworkspace"  # Should convert to lowercase
        assert validate_workspace_slug("my-workspace") == "my-workspace"
        assert validate_workspace_slug("my_workspace") == "my_workspace"
        assert validate_workspace_slug("my.workspace") == "my.workspace"

    def test_validate_workspace_uuid_valid(self):
        """Test valid workspace UUIDs."""
        uuid = "123e4567-e89b-12d3-a456-426614174000"
        assert validate_workspace_slug(uuid) == uuid.lower()

        uuid_upper = "123E4567-E89B-12D3-A456-426614174000"
        assert validate_workspace_slug(uuid_upper) == uuid_upper.lower()

        uuid_braces = "{123e4567-e89b-12d3-a456-426614174000}"
        assert validate_workspace_slug(uuid_braces) == uuid_braces.lower()

    def test_validate_email_valid(self):
        """Test valid email addresses."""
        assert validate_email("user@example.com") == "user@example.com"
        assert validate_email("USER@EXAMPLE.COM") == "user@example.com"  # Should convert to lowercase
        assert validate_email("user.name@example.com") == "user.name@example.com"
        assert validate_email("user+tag@example.com") == "user+tag@example.com"
        assert validate_email("user123@example-domain.co.uk") == "user123@example-domain.co.uk"

    def test_validate_email_invalid(self):
        """Test invalid email addresses."""
        with pytest.raises(ValidationError):
            validate_email("")  # Empty

        with pytest.raises(ValidationError):
            validate_email("user")  # No @ symbol

        with pytest.raises(ValidationError):
            validate_email("user@")  # No domain

        with pytest.raises(ValidationError):
            validate_email("@example.com")  # No user

        with pytest.raises(ValidationError):
            validate_email("user@example")  # No TLD

        with pytest.raises(ValidationError):
            validate_email("user space@example.com")  # Space in user part

    def test_validate_user_identifier_email(self):
        """Test user identifier validation with email."""
        assert validate_user_identifier("user@example.com") == "user@example.com"

    def test_validate_user_identifier_uuid(self):
        """Test user identifier validation with UUID."""
        uuid = "123e4567-e89b-12d3-a456-426614174000"
        assert validate_user_identifier(uuid) == uuid.lower()

        uuid_braces = "{123e4567-e89b-12d3-a456-426614174000}"
        assert validate_user_identifier(uuid_braces) == uuid_braces.lower()

    def test_validate_permission_level_valid(self):
        """Test valid permission levels."""
        assert validate_permission_level("read") == "read"
        assert validate_permission_level("READ") == "read"  # Should convert to lowercase
        assert validate_permission_level("write") == "write"
        assert validate_permission_level("admin") == "admin"

    def test_validate_permission_level_invalid(self):
        """Test invalid permission levels."""
        with pytest.raises(ValidationError):
            validate_permission_level("")  # Empty

        with pytest.raises(ValidationError):
            validate_permission_level("invalid")  # Not in allowed list

        with pytest.raises(ValidationError):
            validate_permission_level("owner")  # Not in allowed list

    def test_validate_branch_name_valid(self):
        """Test valid branch names."""
        assert validate_branch_name("main") == "main"
        assert validate_branch_name("feature/new-feature") == "feature/new-feature"
        assert validate_branch_name("hotfix-123") == "hotfix-123"
        assert validate_branch_name("release/v1.0.0") == "release/v1.0.0"

    def test_validate_branch_name_invalid(self):
        """Test invalid branch names."""
        with pytest.raises(ValidationError):
            validate_branch_name("")  # Empty

        with pytest.raises(ValidationError):
            validate_branch_name("feature..fix")  # Contains ..

        with pytest.raises(ValidationError):
            validate_branch_name("feature@{fix}")  # Contains @{

        with pytest.raises(ValidationError):
            validate_branch_name("feature\\fix")  # Contains backslash

        with pytest.raises(ValidationError):
            validate_branch_name("feature fix")  # Contains space

        with pytest.raises(ValidationError):
            validate_branch_name("feature~fix")  # Contains ~

        with pytest.raises(ValidationError):
            validate_branch_name("feature^fix")  # Contains ^

        with pytest.raises(ValidationError):
            validate_branch_name("feature:fix")  # Contains :

        with pytest.raises(ValidationError):
            validate_branch_name("feature?fix")  # Contains ?

        with pytest.raises(ValidationError):
            validate_branch_name("feature*fix")  # Contains *

        with pytest.raises(ValidationError):
            validate_branch_name("feature[fix]")  # Contains [

        with pytest.raises(ValidationError):
            validate_branch_name("feature.lock")  # Ends with .lock

        with pytest.raises(ValidationError):
            validate_branch_name(".feature")  # Starts with .

        with pytest.raises(ValidationError):
            validate_branch_name("feature/")  # Ends with /

        with pytest.raises(ValidationError):
            validate_branch_name("feature/.fix")  # Contains /.

    def test_validate_non_empty_string_valid(self):
        """Test valid non-empty strings."""
        assert validate_non_empty_string("test", "field") == "test"
        assert validate_non_empty_string("  test  ", "field") == "test"  # Should strip whitespace

    def test_validate_non_empty_string_invalid(self):
        """Test invalid non-empty strings."""
        with pytest.raises(ValidationError):
            validate_non_empty_string("", "field")  # Empty

        with pytest.raises(ValidationError):
            validate_non_empty_string("   ", "field")  # Only whitespace
