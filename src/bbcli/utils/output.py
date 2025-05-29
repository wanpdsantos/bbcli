"""
Output formatting utilities for bbcli.

This module provides functions for formatting and displaying output in various formats
including text, JSON, and YAML.
"""

import json
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table


class OutputFormatter:
    """Handles output formatting for different output types."""

    def __init__(self, format_type: str = "text", console: Console | None = None) -> None:
        """
        Initialize the output formatter.

        Args:
            format_type: Output format ('text', 'json', 'yaml')
            console: Rich console instance for text output
        """
        self.format_type = format_type.lower()
        self.console = console or Console()

    def format_output(self, data: Any, title: str | None = None) -> None:
        """
        Format and display output based on the configured format.

        Args:
            data: Data to format and display
            title: Optional title for the output
        """
        if self.format_type == "json":
            self._format_json(data)
        elif self.format_type == "yaml":
            self._format_yaml(data)
        else:
            self._format_text(data, title)

    def _format_json(self, data: Any) -> None:
        """Format output as JSON."""
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        self.console.print(json_str)

    def _format_yaml(self, data: Any) -> None:
        """Format output as YAML."""
        yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        self.console.print(yaml_str.rstrip())

    def _format_text(self, data: Any, title: str | None = None) -> None:
        """Format output as human-readable text."""
        if isinstance(data, dict):
            self._format_dict_as_text(data, title)
        elif isinstance(data, list):
            self._format_list_as_text(data, title)
        else:
            if title:
                self.console.print(f"[bold]{title}:[/bold] {data}")
            else:
                self.console.print(str(data))

    def _format_dict_as_text(self, data: dict[str, Any], title: str | None = None) -> None:
        """Format a dictionary as readable text."""
        if title:
            self.console.print(f"\n[bold green]{title}[/bold green]")

        # Create a table for key-value pairs
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        for key, value in data.items():
            value_str = json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value)

            table.add_row(key.replace("_", " ").title(), value_str)

        self.console.print(table)

    def _format_list_as_text(self, data: list, title: str | None = None) -> None:
        """Format a list as readable text."""
        if title:
            self.console.print(f"\n[bold green]{title}[/bold green]")

        if not data:
            self.console.print("[dim]No items found[/dim]")
            return

        # If list contains dictionaries, format as table
        if data and isinstance(data[0], dict):
            self._format_list_of_dicts_as_table(data)
        else:
            # Simple list
            for i, item in enumerate(data, 1):
                self.console.print(f"{i}. {item}")

    def _format_list_of_dicts_as_table(self, data: list) -> None:
        """Format a list of dictionaries as a table."""
        if not data:
            return

        # Get all unique keys from all dictionaries
        all_keys: set[str] = set()
        for item in data:
            if isinstance(item, dict):
                all_keys.update(item.keys())

        # Create table with headers
        table = Table()
        for key in sorted(all_keys):
            table.add_column(key.replace("_", " ").title(), style="cyan")

        # Add rows
        for item in data:
            if isinstance(item, dict):
                row = []
                for key in sorted(all_keys):
                    value = item.get(key, "")
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=2)
                    row.append(str(value))
                table.add_row(*row)

        self.console.print(table)

    def success(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Display a success message."""
        if self.format_type in ["json", "yaml"]:
            output_data = {"status": "success", "message": message}
            if details:
                output_data.update(details)
            self.format_output(output_data)
        else:
            self.console.print(f"[green]✅ {message}[/green]")
            if details:
                self._format_dict_as_text(details)

    def error(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Display an error message."""
        if self.format_type in ["json", "yaml"]:
            output_data = {"status": "error", "message": message}
            if details:
                output_data.update(details)
            self.format_output(output_data)
        else:
            self.console.print(f"[red]❌ {message}[/red]")
            if details:
                self._format_dict_as_text(details)

    def warning(self, message: str) -> None:
        """Display a warning message."""
        if self.format_type in ["json", "yaml"]:
            self.format_output({"status": "warning", "message": message})
        else:
            self.console.print(f"[yellow]⚠️  {message}[/yellow]")

    def info(self, message: str) -> None:
        """Display an info message."""
        if self.format_type in ["json", "yaml"]:
            self.format_output({"status": "info", "message": message})
        else:
            self.console.print(f"[blue]ℹ️  {message}[/blue]")


def create_progress_spinner(description: str = "Working...") -> Any:
    """Create a progress spinner for long-running operations."""
    from rich.live import Live
    from rich.spinner import Spinner

    spinner = Spinner("dots", text=description)
    return Live(spinner, refresh_per_second=10)
