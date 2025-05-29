"""
Main entry point for the bbcli command-line interface.

This module sets up the main CLI group and registers all command modules.
"""

import os
import sys

import click
from rich.console import Console
from rich.traceback import install

from bbcli import __version__
from bbcli.cli import auth, branch, oauth_auth, project, repo
from bbcli.core.exceptions import BBCLIError
from bbcli.utils.output import OutputFormatter

# Install rich traceback handler only in development mode
if os.getenv("BBCLI_DEBUG") or os.getenv("DEBUG"):
    install(show_locals=True)

# Global console instance
console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="bbcli")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output for debugging.",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "yaml"], case_sensitive=False),
    default="text",
    help="Output format (default: text).",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, output: str) -> None:
    """
    bbcli - A command-line interface for interacting with the Bitbucket API.

    Manage Bitbucket projects, repositories, users, and branch permissions
    through a simple and intuitive command-line interface.

    Examples:
        bbcli auth login                    # Set up authentication
        bbcli project create MYPROJ         # Create a new project
        bbcli repo create my-repo           # Create a new repository
        bbcli repo user add my-repo         # Add user to repository

    For more information on specific commands, use:
        bbcli <command> --help
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store global options in context
    ctx.obj["verbose"] = verbose
    ctx.obj["output_format"] = output.lower()
    ctx.obj["console"] = console
    ctx.obj["formatter"] = OutputFormatter(output.lower(), console)


# Register command groups
cli.add_command(auth.auth)
cli.add_command(oauth_auth.oauth)
cli.add_command(project.project)
cli.add_command(repo.repo)
cli.add_command(branch.branch)


def handle_exception(exc: Exception) -> None:
    """Handle exceptions and display appropriate error messages."""
    if isinstance(exc, BBCLIError):
        console.print(f"[red]Error:[/red] {exc}")
        if exc.suggestion:
            console.print(f"[yellow]Suggestion:[/yellow] {exc.suggestion}")
        sys.exit(exc.exit_code)
    elif isinstance(exc, click.ClickException):
        # Let Click handle its own exceptions
        exc.show()
        sys.exit(exc.exit_code)
    else:
        # Unexpected error
        console.print(f"[red]Unexpected error:[/red] {exc}")
        console.print(
            "[yellow]This is likely a bug. Please report it at:[/yellow] " "https://github.com/yourusername/bbcli/issues",
        )
        sys.exit(1)


def main() -> None:
    """Main entry point with exception handling."""
    try:
        cli(ctx=click.Context(cli), verbose=False, output="text")
    except Exception as exc:
        handle_exception(exc)


if __name__ == "__main__":
    main()
