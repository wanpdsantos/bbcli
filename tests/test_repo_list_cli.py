"""
Tests for repository list CLI command.
"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from rich.console import Console

from bbcli.cli.repo import repo
from bbcli.core.exceptions import BBCLIError
from bbcli.utils.output import OutputFormatter


class TestRepoListCLI:
    """Test cases for repository list CLI command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_context(self):
        """Create mock CLI context."""
        console = Console()
        formatter = OutputFormatter("text", console)
        return {
            "console": console,
            "formatter": formatter,
            "verbose": False,
            "output_format": "text",
        }

    @pytest.fixture
    def sample_repositories(self):
        """Sample repository data from Bitbucket API."""
        return {
            "values": [
                {
                    "name": "my-web-app",
                    "full_name": "myworkspace/my-web-app",
                    "description": "A web application built with React",
                    "is_private": True,
                    "language": "JavaScript",
                    "size": 1024000,
                    "updated_on": "2024-01-15T10:30:00.000000+00:00",
                    "project": {"key": "WEBAPP", "name": "Web Applications"},
                    "links": {
                        "html": {"href": "https://bitbucket.org/myworkspace/my-web-app"},
                        "clone": [
                            {
                                "name": "https",
                                "href": "https://bitbucket.org/myworkspace/my-web-app.git",
                            }
                        ],
                    },
                },
                {
                    "name": "api-service",
                    "full_name": "myworkspace/api-service",
                    "description": "REST API service for the application",
                    "is_private": False,
                    "language": "Python",
                    "size": 512000,
                    "updated_on": "2024-01-10T14:20:00.000000+00:00",
                    "project": {"key": "BACKEND", "name": "Backend Services"},
                    "links": {
                        "html": {"href": "https://bitbucket.org/myworkspace/api-service"},
                        "clone": [
                            {
                                "name": "https",
                                "href": "https://bitbucket.org/myworkspace/api-service.git",
                            }
                        ],
                    },
                },
            ],
            "next": None,
        }

    def test_repo_list_basic(self, runner, mock_context, sample_repositories):
        """Test basic repository listing."""
        with patch("bbcli.cli.repo.get_api_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get.return_value = sample_repositories
            mock_get_client.return_value = mock_client

            result = runner.invoke(repo, ["list", "--workspace", "myworkspace"], obj=mock_context)

            assert result.exit_code == 0
            assert "my-web-app" in result.output
            assert "api-service" in result.output
            assert "Found 2 repositories" in result.output

            # Verify API call
            mock_client.get.assert_called_once_with("/repositories/myworkspace", params={"sort": "-updated_on"})

    def test_repo_list_with_project_filter(self, runner, mock_context, sample_repositories):
        """Test repository listing with project filter."""
        # Filter to only return WEBAPP project repos
        filtered_repos = {
            "values": [sample_repositories["values"][0]],  # Only my-web-app
            "next": None,
        }

        with patch("bbcli.cli.repo.get_api_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get.return_value = filtered_repos
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                repo,
                ["list", "--workspace", "myworkspace", "--project", "WEBAPP"],
                obj=mock_context,
            )

            assert result.exit_code == 0
            assert "my-web-app" in result.output
            assert "api-service" not in result.output

            # Verify API call with project filter
            mock_client.get.assert_called_once_with(
                "/repositories/myworkspace",
                params={"q": 'project.key="WEBAPP"', "sort": "-updated_on"},
            )

    def test_repo_list_with_query_filter(self, runner, mock_context, sample_repositories):
        """Test repository listing with name query filter."""
        # Filter to only return repos matching "web"
        filtered_repos = {
            "values": [sample_repositories["values"][0]],  # Only my-web-app
            "next": None,
        }

        with patch("bbcli.cli.repo.get_api_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get.return_value = filtered_repos
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                repo,
                ["list", "--workspace", "myworkspace", "--query", "web"],
                obj=mock_context,
            )

            assert result.exit_code == 0
            assert "my-web-app" in result.output

            # Verify API call with query filter
            mock_client.get.assert_called_once_with(
                "/repositories/myworkspace",
                params={"q": 'name~"web"', "sort": "-updated_on"},
            )

    def test_repo_list_with_both_filters(self, runner, mock_context, sample_repositories):
        """Test repository listing with both project and query filters."""
        filtered_repos = {"values": [sample_repositories["values"][0]], "next": None}

        with patch("bbcli.cli.repo.get_api_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get.return_value = filtered_repos
            mock_get_client.return_value = mock_client

            result = runner.invoke(
                repo,
                [
                    "list",
                    "--workspace",
                    "myworkspace",
                    "--project",
                    "WEBAPP",
                    "--query",
                    "web",
                ],
                obj=mock_context,
            )

            assert result.exit_code == 0

            # Verify API call with combined filters
            mock_client.get.assert_called_once_with(
                "/repositories/myworkspace",
                params={
                    "q": 'project.key="WEBAPP" AND name~"web"',
                    "sort": "-updated_on",
                },
            )

    def test_repo_list_pagination(self, runner, mock_context):
        """Test repository listing with pagination."""
        # First page
        page1 = {
            "values": [
                {
                    "name": "repo1",
                    "full_name": "myworkspace/repo1",
                    "description": "First repository",
                    "is_private": True,
                    "language": "Python",
                    "size": 1000,
                    "updated_on": "2024-01-15T10:30:00.000000+00:00",
                    "project": {"key": "PROJ1"},
                    "links": {
                        "html": {"href": "https://bitbucket.org/myworkspace/repo1"},
                        "clone": [
                            {
                                "name": "https",
                                "href": "https://bitbucket.org/myworkspace/repo1.git",
                            }
                        ],
                    },
                }
            ],
            "next": "https://api.bitbucket.org/2.0/repositories/myworkspace?page=2",
        }

        # Second page
        page2 = {
            "values": [
                {
                    "name": "repo2",
                    "full_name": "myworkspace/repo2",
                    "description": "Second repository",
                    "is_private": False,
                    "language": "JavaScript",
                    "size": 2000,
                    "updated_on": "2024-01-14T10:30:00.000000+00:00",
                    "project": {"key": "PROJ2"},
                    "links": {
                        "html": {"href": "https://bitbucket.org/myworkspace/repo2"},
                        "clone": [
                            {
                                "name": "https",
                                "href": "https://bitbucket.org/myworkspace/repo2.git",
                            }
                        ],
                    },
                }
            ],
            "next": None,
        }

        with patch("bbcli.cli.repo.get_api_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get.side_effect = [page1, page2]
            mock_get_client.return_value = mock_client

            result = runner.invoke(repo, ["list", "--workspace", "myworkspace"], obj=mock_context)

            assert result.exit_code == 0
            assert "repo1" in result.output
            assert "repo2" in result.output
            assert "Found 2 repositories" in result.output

            # Verify both API calls
            assert mock_client.get.call_count == 2
            mock_client.get.assert_any_call("/repositories/myworkspace", params={"sort": "-updated_on"})
            mock_client.get.assert_any_call("/2.0/repositories/myworkspace?page=2", params=None)

    def test_repo_list_no_repositories(self, runner, mock_context):
        """Test repository listing when no repositories found."""
        empty_response = {"values": [], "next": None}

        with patch("bbcli.cli.repo.get_api_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get.return_value = empty_response
            mock_get_client.return_value = mock_client

            result = runner.invoke(repo, ["list", "--workspace", "myworkspace"], obj=mock_context)

            assert result.exit_code == 0
            assert "No repositories found in workspace 'myworkspace'" in result.output

    def test_repo_list_json_output(self, runner, sample_repositories):
        """Test repository listing with JSON output."""
        console = Console()
        formatter = OutputFormatter("json", console)
        mock_context = {
            "console": console,
            "formatter": formatter,
            "verbose": False,
            "output_format": "json",
        }

        with patch("bbcli.cli.repo.get_api_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get.return_value = sample_repositories
            mock_get_client.return_value = mock_client

            result = runner.invoke(repo, ["list", "--workspace", "myworkspace"], obj=mock_context)

            assert result.exit_code == 0
            # Should contain JSON structure
            assert '"workspace": "myworkspace"' in result.output
            assert '"total_count": 2' in result.output
            assert '"repositories":' in result.output

    def test_repo_list_missing_workspace(self, runner, mock_context):
        """Test repository listing without required workspace parameter."""
        result = runner.invoke(repo, ["list"], obj=mock_context)

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output

    def test_repo_list_api_error(self, runner, mock_context):
        """Test repository listing when API returns an error."""
        with patch("bbcli.cli.repo.get_api_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get.side_effect = BBCLIError("Workspace not found")
            mock_get_client.return_value = mock_client

            # Test that BBCLIError is properly raised
            with pytest.raises(BBCLIError) as exc_info:
                runner.invoke(
                    repo,
                    ["list", "--workspace", "invalid-workspace"],
                    obj=mock_context,
                    catch_exceptions=False,
                )

            assert "Workspace not found" in str(exc_info.value)
