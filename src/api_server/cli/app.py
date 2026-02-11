"""Main CLI application."""

import typer

from api_server.cli.commands import db
from api_server.services.di import register_core_services
from api_server.services.registry import get_service_registry

app = typer.Typer(
    name="api-server-cli",
    help="API Server CLI - Administrative tools",
    no_args_is_help=True,
)


@app.callback()
def main_callback():
    """Global options for all commands."""
    # Initialize service registry for CLI using shared DI module
    registry = get_service_registry()
    register_core_services(registry)


# Register command groups
app.add_typer(db.app, name="db")
