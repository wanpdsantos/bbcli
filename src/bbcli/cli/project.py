"""
Project management commands for bbcli.

This module provides commands for creating and managing Bitbucket projects.
"""

import click

from bbcli.core.api_client import get_api_client
from bbcli.core.exceptions import BBCLIError
from bbcli.utils.output import OutputFormatter
from bbcli.utils.validation import validate_non_empty_string, validate_project_key, validate_workspace_slug


@click.group()
def project() -> None:
    """Manage Bitbucket projects."""


@project.command()
@click.argument("project_key")
@click.option("--name", "-n", required=True, help="Display name for the project")
@click.option("--description", "-d", help="Description for the project")
@click.option(
    "--private",
    "is_private",
    flag_value=True,
    default=True,
    help="Create a private project (default)",
)
@click.option("--public", "is_private", flag_value=False, help="Create a public project")
@click.option(
    "--workspace",
    "-w",
    required=True,
    help="Workspace slug or UUID where the project will be created",
)
@click.pass_context
def create(
    ctx: click.Context,
    project_key: str,
    name: str,
    description: str | None,
    is_private: bool,
    workspace: str,
) -> None:
    """
    Create a new Bitbucket project.

    PROJECT_KEY is the unique identifier for the project (e.g., "MARSROVER").
    It should be uppercase and alphanumeric.

    Examples:
        bbcli project create MYPROJ --name "My Project" --workspace myworkspace
        bbcli project create WEBAPP --name "Web Application" --description "Main web app" --public --workspace myworkspace
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        project_key = validate_project_key(project_key)
        name = validate_non_empty_string(name, "Project name")
        workspace = validate_workspace_slug(workspace)

        if description:
            description = validate_non_empty_string(description, "Project description")

        # Prepare project data
        project_data = {
            "name": name,
            "key": project_key,
            "is_private": is_private,
        }

        if description:
            project_data["description"] = description

        # Create project via API
        api_client = get_api_client()

        formatter.info(f"Creating project '{project_key}' in workspace '{workspace}'...")

        response = api_client.post(f"/workspaces/{workspace}/projects", json_data=project_data)

        # Format success output
        project_info = {
            "key": response.get("key"),
            "name": response.get("name"),
            "description": response.get("description", ""),
            "workspace": workspace,
            "visibility": "Private" if response.get("is_private", True) else "Public",
            "created_on": response.get("created_on", ""),
            "link": response.get("links", {}).get("html", {}).get("href", ""),
        }

        formatter.success(
            f"Project '{project_key}' ({name}) created successfully",
            details=project_info,
        )

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to create project: {e}") from e


@project.command()
@click.argument("project_key")
@click.option("--workspace", "-w", required=True, help="Workspace slug or UUID")
@click.pass_context
def show(
    ctx: click.Context,
    project_key: str,
    workspace: str,
) -> None:
    """
    Show details of a Bitbucket project.

    PROJECT_KEY is the unique identifier of the project to show.

    Examples:
        bbcli project show MYPROJ --workspace myworkspace
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        project_key = validate_project_key(project_key)
        workspace = validate_workspace_slug(workspace)

        # Get project via API
        api_client = get_api_client()

        response = api_client.get(f"/workspaces/{workspace}/projects/{project_key}")

        # Format output
        project_info = {
            "key": response.get("key"),
            "name": response.get("name"),
            "description": response.get("description", ""),
            "workspace": workspace,
            "visibility": "Private" if response.get("is_private", True) else "Public",
            "created_on": response.get("created_on", ""),
            "updated_on": response.get("updated_on", ""),
            "link": response.get("links", {}).get("html", {}).get("href", ""),
        }

        formatter.format_output(project_info, f"Project {project_key}")

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to get project information: {e}") from e


@project.command()
@click.option("--workspace", "-w", required=True, help="Workspace slug or UUID")
@click.pass_context
def list(
    ctx: click.Context,
    workspace: str,
) -> None:
    """
    List all projects in a workspace.

    Examples:
        bbcli project list --workspace myworkspace
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        workspace = validate_workspace_slug(workspace)

        # Get projects via API
        api_client = get_api_client()

        response = api_client.get(f"/workspaces/{workspace}/projects")

        projects = response.get("values", [])

        if not projects:
            formatter.info(f"No projects found in workspace '{workspace}'")
            return

        # Format project list
        project_list = []
        for proj in projects:
            project_list.append(
                {
                    "key": proj.get("key"),
                    "name": proj.get("name"),
                    "visibility": ("Private" if proj.get("is_private", True) else "Public"),
                    "created_on": proj.get("created_on", "")[:10],  # Just the date part
                }
            )

        formatter.format_output(project_list, f"Projects in {workspace}")

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to list projects: {e}") from e
