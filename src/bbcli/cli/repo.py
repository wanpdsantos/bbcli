"""
Repository management commands for bbcli.

This module provides commands for creating and managing Bitbucket repositories,
including user management and listing repositories.
"""

from typing import Any

import click
from rich.table import Table

from bbcli.core.api_client import get_api_client
from bbcli.core.exceptions import BBCLIError
from bbcli.utils.output import OutputFormatter
from bbcli.utils.validation import (
    validate_non_empty_string,
    validate_permission_level,
    validate_project_key,
    validate_repository_slug,
    validate_user_identifier,
    validate_workspace_slug,
)


@click.group()
def repo() -> None:
    """Manage Bitbucket repositories."""


@repo.command()
@click.argument("repository_slug")
@click.option(
    "--project",
    "-p",
    required=True,
    help="Project key where the repository will be created",
)
@click.option("--description", "-d", help="Description for the repository")
@click.option(
    "--private",
    "is_private",
    flag_value=True,
    default=True,
    help="Create a private repository (default)",
)
@click.option("--public", "is_private", flag_value=False, help="Create a public repository")
@click.option("--mainbranch", help="Name of the main branch (e.g., 'main', 'master')")
@click.option("--language", help="Programming language for the repository")
@click.option(
    "--fork-policy",
    type=click.Choice(["allow_forks", "no_public_forks", "no_forks"]),
    help="Fork policy for the repository",
)
@click.option("--workspace", "-w", required=True, help="Workspace slug or UUID")
@click.pass_context
def create(
    ctx: click.Context,
    repository_slug: str,
    project: str,
    description: str | None,
    is_private: bool,
    mainbranch: str | None,
    language: str | None,
    fork_policy: str | None,
    workspace: str,
) -> None:
    """
    Create a new Bitbucket repository.

    REPOSITORY_SLUG is the unique identifier for the repository (e.g., "my-app").
    It should be lowercase with hyphens for spaces.

    Examples:
        bbcli repo create my-app --project MYPROJ --workspace myworkspace
        bbcli repo create web-frontend --project WEBAPP --description "Frontend application" --public --workspace myworkspace
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        repository_slug = validate_repository_slug(repository_slug)
        project = validate_project_key(project)
        workspace = validate_workspace_slug(workspace)

        if description:
            description = validate_non_empty_string(description, "Repository description")

        # Prepare repository data
        repo_data = {
            "name": repository_slug,
            "is_private": is_private,
            "project": {"key": project},
        }

        if description:
            repo_data["description"] = description

        if mainbranch:
            repo_data["mainbranch"] = {"name": mainbranch}

        if language:
            repo_data["language"] = language

        if fork_policy:
            repo_data["fork_policy"] = fork_policy

        # Create repository via API
        api_client = get_api_client()

        formatter.info(f"Creating repository '{repository_slug}' in project '{project}'...")

        response = api_client.post(f"/repositories/{workspace}/{repository_slug}", json_data=repo_data)

        # Format success output
        repo_info = {
            "slug": response.get("name"),
            "full_name": response.get("full_name"),
            "project": project,
            "workspace": workspace,
            "description": response.get("description", ""),
            "visibility": "Private" if response.get("is_private", True) else "Public",
            "language": response.get("language", ""),
            "size": response.get("size", 0),
            "created_on": response.get("created_on", ""),
            "https_clone_url": response.get("links", {}).get("clone", [{}])[0].get("href", ""),
            "ssh_clone_url": next(
                (link.get("href", "") for link in response.get("links", {}).get("clone", []) if link.get("name") == "ssh"),
                "",
            ),
            "link": response.get("links", {}).get("html", {}).get("href", ""),
        }

        formatter.success(
            f"Repository '{repository_slug}' created successfully in project '{project}'",
            details=repo_info,
        )

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to create repository: {e}") from e


@repo.command()
@click.option("--workspace", "-w", required=True, help="Workspace slug or UUID")
@click.option(
    "--project",
    "-p",
    help="Filter repositories by project key",
)
@click.option(
    "--query",
    "-q",
    help="Filter repositories by name (text search)",
)
@click.pass_context
def list(
    ctx: click.Context,
    workspace: str,
    project: str | None,
    query: str | None,
) -> None:
    """
    List repositories in a workspace.

    This command lists all repositories in the specified workspace that you have access to.
    You can filter the results by project key or search for repositories by name.

    Examples:
        bbcli repo list --workspace myworkspace
        bbcli repo list --workspace myworkspace --project MYPROJ
        bbcli repo list --workspace myworkspace --query "web"
        bbcli repo list --workspace myworkspace --project MYPROJ --query "frontend"
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        workspace = validate_workspace_slug(workspace)
        if project:
            project = validate_project_key(project)
        if query:
            query = validate_non_empty_string(query, "Query")

        # Get API client
        api_client = get_api_client()

        formatter.info(f"Fetching repositories from workspace '{workspace}'...")

        # Build query parameters
        initial_params: dict[str, Any] = {}

        # Add project filter if specified
        if project:
            initial_params["q"] = f'project.key="{project}"'

        # Add name query filter if specified
        if query:
            name_filter = f'name~"{query}"'
            if "q" in initial_params:
                initial_params["q"] += f" AND {name_filter}"
            else:
                initial_params["q"] = name_filter

        # Sort by updated date (most recent first)
        initial_params["sort"] = "-updated_on"

        # Fetch repositories with pagination
        repositories = []
        page_url: str | None = f"/repositories/{workspace}"
        current_params: dict[str, Any] | None = initial_params

        while page_url:
            response = api_client.get(page_url, params=current_params)

            # Add repositories from this page
            repositories.extend(response.get("values", []))

            # Get next page URL
            next_page_url = response.get("next")
            if next_page_url:
                # Extract relative path from full URL
                from urllib.parse import urlparse

                parsed_url = urlparse(next_page_url)
                page_url = parsed_url.path + ("?" + parsed_url.query if parsed_url.query else "")
                current_params = None  # Don't pass params for subsequent pages as they're in the URL
            else:
                page_url = None

        if not repositories:
            if project and query:
                formatter.info(f"No repositories found in workspace '{workspace}' for project '{project}' matching '{query}'")
            elif project:
                formatter.info(f"No repositories found in workspace '{workspace}' for project '{project}'")
            elif query:
                formatter.info(f"No repositories found in workspace '{workspace}' matching '{query}'")
            else:
                formatter.info(f"No repositories found in workspace '{workspace}'")
            return

        # Format repository data
        repo_data = []
        for repo in repositories:
            # Parse dates
            updated_on = repo.get("updated_on", "")
            if updated_on:
                try:
                    # Parse ISO format date and format it nicely
                    from datetime import datetime

                    dt = datetime.fromisoformat(updated_on.replace("Z", "+00:00"))
                    updated_on = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except (ValueError, AttributeError):
                    # Keep original if parsing fails
                    pass

            repo_info = {
                "name": repo.get("name", ""),
                "project_key": repo.get("project", {}).get("key", ""),
                "description": repo.get("description", "")[:100] + ("..." if len(repo.get("description", "")) > 100 else ""),
                "updated_on": updated_on,
                "is_private": "Private" if repo.get("is_private", True) else "Public",
                "language": repo.get("language", ""),
                "size": repo.get("size", 0),
                "full_name": repo.get("full_name", ""),
                "clone_url": next(
                    (link.get("href", "") for link in repo.get("links", {}).get("clone", []) if link.get("name") == "https"),
                    "",
                ),
                "web_url": repo.get("links", {}).get("html", {}).get("href", ""),
            }
            repo_data.append(repo_info)

        # Display results
        if formatter.format_type == "text":
            # Create rich table for text output
            table = Table(title=f"Repositories in {workspace}")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Project", style="green")
            table.add_column("Description", style="white")
            table.add_column("Updated", style="yellow")
            table.add_column("Visibility", style="magenta")

            for repo in repo_data:
                table.add_row(
                    repo["name"],
                    repo["project_key"],
                    repo["description"],
                    repo["updated_on"],
                    repo["is_private"],
                )

            formatter.console.print(table)
            formatter.console.print(f"\n[green]Found {len(repositories)} repositories[/green]")
        else:
            # JSON/YAML output
            output_data = {
                "workspace": workspace,
                "total_count": len(repositories),
                "filters": {
                    "project": project,
                    "query": query,
                },
                "repositories": repo_data,
            }
            formatter.format_output(output_data, f"Repositories in {workspace}")

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to list repositories: {e}") from e


@repo.group()
def user() -> None:
    """Manage repository users and permissions."""


@user.command()
@click.argument("repository_slug")
@click.option("--project", "-p", required=True, help="Project key")
@click.option("--user", "-u", required=True, help="User account ID or email address")
@click.option(
    "--permission",
    "-r",
    required=True,
    type=click.Choice(["read", "write", "admin"]),
    help="Permission level to grant",
)
@click.option("--workspace", "-w", required=True, help="Workspace slug or UUID")
@click.pass_context
def add(
    ctx: click.Context,
    repository_slug: str,
    project: str,
    user_param: str,
    permission: str,
    workspace: str,
) -> None:
    """
    Add a user to a repository with specified permissions.

    Examples:
        bbcli repo user add my-repo --project MYPROJ --user user@example.com --permission write --workspace myworkspace
        bbcli repo user add my-repo --project MYPROJ --user {account-id} --permission admin --workspace myworkspace
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        repository_slug = validate_repository_slug(repository_slug)
        project = validate_project_key(project)
        user_input = validate_user_identifier(user_param)
        permission = validate_permission_level(permission)
        workspace = validate_workspace_slug(workspace)

        # Add user via API
        api_client = get_api_client()

        formatter.info(
            f"Adding user '{user_input}' to repository '{project}/{repository_slug}' with '{permission}' permission..."
        )

        # Prepare user permission data
        permission_data: dict[str, Any] = {
            "type": "repository_permission",
            "user": {},
            "permission": permission,
        }

        # Add appropriate user identifier
        if user_input.startswith("{"):
            permission_data["user"]["account_id"] = user_input
        elif "@" in user_input:
            permission_data["user"]["email"] = user_input

        api_client.put(
            f"/repositories/{workspace}/{repository_slug}/permissions-config/users/{user_input}",
            json_data=permission_data,
        )

        formatter.success(f"User '{user_input}' added to repository '{project}/{repository_slug}' with '{permission}' permission")

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to add user to repository: {e}") from e


@user.command()
@click.argument("repository_slug")
@click.option("--project", "-p", required=True, help="Project key")
@click.option("--user", "-u", required=True, help="User account ID or email address")
@click.option("--workspace", "-w", required=True, help="Workspace slug or UUID")
@click.pass_context
def remove(
    ctx: click.Context,
    repository_slug: str,
    project: str,
    user_param: str,
    workspace: str,
) -> None:
    """
    Remove a user from a repository.

    Examples:
        bbcli repo user remove my-repo --project MYPROJ --user user@example.com --workspace myworkspace
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        repository_slug = validate_repository_slug(repository_slug)
        project = validate_project_key(project)
        user_input = validate_user_identifier(user_param)
        workspace = validate_workspace_slug(workspace)

        # Confirm removal
        if not click.confirm(f"Remove user '{user_input}' from repository '{project}/{repository_slug}'?"):
            formatter.info("User removal cancelled")
            return

        # Remove user via API
        api_client = get_api_client()

        formatter.info(f"Removing user '{user_input}' from repository '{project}/{repository_slug}'...")

        api_client.delete(f"/repositories/{workspace}/{repository_slug}/permissions-config/users/{user_input}")

        formatter.success(f"User '{user_input}' removed from repository '{project}/{repository_slug}'")

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to remove user from repository: {e}") from e
