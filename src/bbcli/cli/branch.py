"""
Branch permission management commands for bbcli.

This module provides commands for managing branch permissions and restrictions
in Bitbucket repositories.
"""

from typing import Any

import click

from bbcli.core.api_client import get_api_client
from bbcli.core.exceptions import BBCLIError
from bbcli.utils.output import OutputFormatter
from bbcli.utils.validation import (
    validate_branch_name,
    validate_project_key,
    validate_repository_slug,
    validate_user_identifier,
    validate_workspace_slug,
)


@click.group()
def branch() -> None:
    """Manage branch permissions and restrictions."""
    pass


@branch.group()
def permission() -> None:
    """Manage branch permissions."""
    pass


@permission.command("exempt-pr")
@click.argument("repository_slug")
@click.option("--project", "-p", required=True, help="Project key")
@click.option("--user", "-u", required=True, help="User account ID or email address to exempt")
@click.option("--branch", "-b", help="Branch name (defaults to repository's default branch)")
@click.option("--workspace", "-w", required=True, help="Workspace slug or UUID")
@click.pass_context
def exempt_pr(
    ctx: click.Context,
    repository_slug: str,
    project: str,
    user: str,
    branch: str | None,
    workspace: str,
) -> None:
    """
    Exempt a user from requiring pull requests for a branch.

    This allows the specified user to push directly to the branch without
    creating a pull request, bypassing any "require pull request" restrictions.

    Examples:
        bbcli branch permission exempt-pr my-repo --project MYPROJ --user user@example.com --workspace myworkspace
        bbcli branch permission exempt-pr my-repo --project MYPROJ --user {account-id} --branch main --workspace myworkspace
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        repository_slug = validate_repository_slug(repository_slug)
        project = validate_project_key(project)
        user = validate_user_identifier(user)
        workspace = validate_workspace_slug(workspace)

        if branch:
            branch = validate_branch_name(branch)

        api_client = get_api_client()

        # Get repository info to determine default branch if not specified
        if not branch:
            formatter.info("Getting repository information...")
            repo_info = api_client.get(f"/repositories/{workspace}/{repository_slug}")
            branch = repo_info.get("mainbranch", {}).get("name", "main")
            formatter.info(f"Using default branch: {branch}")

        # Get existing branch restrictions
        formatter.info(f"Checking existing branch restrictions for '{branch}'...")

        try:
            restrictions_response = api_client.get(f"/repositories/{workspace}/{repository_slug}/branch-restrictions")
            restrictions = restrictions_response.get("values", [])
        except Exception:
            restrictions = []

        # Look for existing "require pull request" restriction
        pr_restriction = None
        for restriction in restrictions:
            if restriction.get("kind") == "require_pull_request_to_merge" and restriction.get("pattern") == branch:
                pr_restriction = restriction
                break

        if not pr_restriction:
            # Create a new restriction that requires pull requests but exempts the user
            formatter.info(f"Creating new pull request requirement for branch '{branch}' with user exemption...")

            restriction_data: dict[str, Any] = {
                "kind": "require_pull_request_to_merge",
                "pattern": branch,
                "users": [],
                "groups": [],
            }

            # Add user if it's a valid account ID
            if user.startswith("{"):
                restriction_data["users"] = [{"account_id": user}]

            if not restriction_data["users"] and "@" in user:
                # If it's an email, we need to resolve it to account ID first
                formatter.warning("Email addresses need to be resolved to account IDs for branch restrictions")
                formatter.info("Please use the account ID format: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}")
                raise BBCLIError(
                    "Branch restrictions require account IDs, not email addresses",
                    suggestion="Use the user's account ID instead of email address",
                )

            api_client.post(
                f"/repositories/{workspace}/{repository_slug}/branch-restrictions",
                json_data=restriction_data,
            )

        else:
            # Update existing restriction to add user exemption
            formatter.info(f"Updating existing pull request restriction for branch '{branch}'...")

            # Get current exempted users
            exempted_users = pr_restriction.get("users", [])

            # Check if user is already exempted
            user_already_exempted = any(u.get("account_id") == user for u in exempted_users)

            if user_already_exempted:
                formatter.info(f"User '{user}' is already exempted from pull request requirements on branch '{branch}'")
                return

            # Add user to exemption list
            if user.startswith("{"):
                exempted_users.append({"account_id": user})
            else:
                formatter.warning("Email addresses need to be resolved to account IDs for branch restrictions")
                raise BBCLIError(
                    "Branch restrictions require account IDs, not email addresses",
                    suggestion="Use the user's account ID instead of email address",
                )

            # Update the restriction
            restriction_data = pr_restriction.copy()
            restriction_data["users"] = exempted_users

            api_client.put(
                f"/repositories/{workspace}/{repository_slug}/branch-restrictions/{pr_restriction['id']}",
                json_data=restriction_data,
            )

        formatter.success(
            f"User '{user}' is now exempt from requiring a pull request to push to branch '{branch}' "
            f"in repository '{project}/{repository_slug}'"
        )

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to exempt user from pull request requirement: {e}") from e


@permission.command("enforce-pr")
@click.argument("repository_slug")
@click.option("--project", "-p", required=True, help="Project key")
@click.option("--user", "-u", required=True, help="User account ID to remove exemption for")
@click.option("--branch", "-b", help="Branch name (defaults to repository's default branch)")
@click.option("--workspace", "-w", required=True, help="Workspace slug or UUID")
@click.pass_context
def enforce_pr(
    ctx: click.Context,
    repository_slug: str,
    project: str,
    user: str,
    branch: str | None,
    workspace: str,
) -> None:
    """
    Remove user exemption from pull request requirements.

    This removes the user from the exemption list, requiring them to use
    pull requests when pushing to the specified branch.

    Examples:
        bbcli branch permission enforce-pr my-repo --project MYPROJ --user {account-id} --workspace myworkspace
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        # Validate inputs
        repository_slug = validate_repository_slug(repository_slug)
        project = validate_project_key(project)
        user = validate_user_identifier(user)
        workspace = validate_workspace_slug(workspace)

        if branch:
            branch = validate_branch_name(branch)

        api_client = get_api_client()

        # Get repository info to determine default branch if not specified
        if not branch:
            repo_info = api_client.get(f"/repositories/{workspace}/{repository_slug}")
            branch = repo_info.get("mainbranch", {}).get("name", "main")

        # Get existing branch restrictions
        restrictions_response = api_client.get(f"/repositories/{workspace}/{repository_slug}/branch-restrictions")
        restrictions = restrictions_response.get("values", [])

        # Find the pull request restriction for this branch
        pr_restriction = None
        for restriction in restrictions:
            if restriction.get("kind") == "require_pull_request_to_merge" and restriction.get("pattern") == branch:
                pr_restriction = restriction
                break

        if not pr_restriction:
            formatter.info(f"No pull request restriction found for branch '{branch}'")
            return

        # Remove user from exemption list
        exempted_users = pr_restriction.get("users", [])
        updated_users = [u for u in exempted_users if u.get("account_id") != user]

        if len(updated_users) == len(exempted_users):
            formatter.info(f"User '{user}' was not exempted from pull request requirements on branch '{branch}'")
            return

        # Update the restriction
        restriction_data = pr_restriction.copy()
        restriction_data["users"] = updated_users

        api_client.put(
            f"/repositories/{workspace}/{repository_slug}/branch-restrictions/{pr_restriction['id']}",
            json_data=restriction_data,
        )

        formatter.success(
            f"User '{user}' now requires pull requests to push to branch '{branch}' in repository '{project}/{repository_slug}'"
        )

    except BBCLIError:
        raise
    except Exception as e:
        raise BBCLIError(f"Failed to enforce pull request requirement: {e}") from e
