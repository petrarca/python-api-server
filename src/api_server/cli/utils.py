"""CLI utility functions shared across commands.

This module contains generic CLI utilities for:
- Path validation
- Directory operations
- Console output
"""

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def validate_path_exists(path: Path, description: str = "Path") -> None:
    """Validate that a path exists.

    Args:
        path: Path to validate
        description: Human-readable description for error message

    Raises:
        typer.Exit: If path does not exist
    """
    if not path.exists():
        console.print(f"[red]Error: {description} does not exist: {path}[/red]")
        raise typer.Exit(1)


def create_subdirectory(parent_dir: Path, subdir_name: str) -> Path:
    """Create a subdirectory within a parent directory.

    Args:
        parent_dir: Parent directory path
        subdir_name: Name of subdirectory to create

    Returns:
        Path to created subdirectory

    Raises:
        typer.Exit: If directory creation fails
    """
    subdir = parent_dir / subdir_name
    try:
        subdir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        console.print(f"[red]Error: Cannot create {subdir_name}/ directory: {e}[/red]")
        raise typer.Exit(1) from e
    return subdir
