"""Database management commands."""

import typer
from rich.console import Console

from api_server.cli.checks.pipeline_builders import build_db_basic_pipeline, build_db_check_pipeline
from api_server.cli.checks.runner import run_readiness_checks
from api_server.database import AlembicManager

app = typer.Typer(help="Database operations")
console = Console()


@app.command()
def check():
    """Check database connection, health, and schema status.

    Validates:
    - Database connection and initialization
    - Database health status
    - Database schema status (alembic setup and version, no migrations)

    This command provides comprehensive database validation including
    schema state verification without performing any migrations.

    Examples:
        api-server-cli db check
        api-server cli db check
    """
    console.print("[bold]Checking database connection, health, and schema...[/bold]\n")

    # Run database readiness checks (connection + health + schema validation)
    run_readiness_checks(build_db_check_pipeline(), "database")

    console.print("[green]Database is healthy, accessible, and schema is up to date![/green]")


@app.command()
def upgrade(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt and proceed with migration automatically",
    ),
):
    """Upgrade database to latest schema version.

    Performs database migration with user confirmation:
    1. Run basic checks (database initialization and health)
    2. Check if migration is needed using AlembicManager
    3. Ask for user confirmation if migration is needed
    4. Perform migration using AlembicManager
    5. Validate schema after migration

    Examples:
        api-server-cli db upgrade
        api-server-cli db upgrade --yes
        api-server cli db upgrade -y
    """
    console.print("[bold]Upgrading database to latest version...[/bold]\n")

    # Step 1: Run basic checks (should always pass)
    console.print("[bold]Step 1: Running basic database checks...[/bold]")
    run_readiness_checks(build_db_basic_pipeline(), "basic database validation")
    console.print("[green]Basic database checks passed[/green]\n")

    # Step 2: Check if migration is needed
    console.print("[bold]Step 2: Checking if migration is needed...[/bold]")
    alembic_manager = AlembicManager()
    message, details, is_success = alembic_manager.validate_schema_state()

    if is_success:
        console.print("[green]Database is already at latest version[/green]")
        console.print(f"[dim]Current revision: {details.get('current_revision', 'Unknown')}[/dim]")
        return

    console.print("[yellow]Database upgrade needed:[/yellow]")
    console.print(f"[dim]{message}[/dim]")
    console.print(f"[dim]Current: {details.get('current_revision', 'Unknown')}[/dim]")
    console.print(f"[dim]Head: {details.get('head_revision', 'Unknown')}[/dim]\n")

    # Step 3: Ask for confirmation unless --yes flag is provided
    if not yes:
        console.print("[yellow]This will upgrade your database to the latest version.[/yellow]")
        console.print("[yellow]The upgrade process will modify your database schema.[/yellow]")
        if not typer.confirm("Proceed with database upgrade?"):
            console.print("[yellow]Upgrade cancelled.[/yellow]")
            raise typer.Exit(0)

    # Step 4: Perform upgrade using AlembicManager
    console.print("[bold]Step 3: Performing database upgrade...[/bold]")
    try:
        success = alembic_manager.perform_migration()
        if success:
            console.print("[green]Database upgrade completed successfully[/green]\n")
        else:
            console.print("[red]Database upgrade failed[/red]")
            raise typer.Exit(1)
    except (OSError, ValueError, RuntimeError) as e:
        console.print(f"[red]Upgrade error: {e!s}[/red]")
        raise typer.Exit(1) from None

    # Step 5: Validate schema after upgrade using same pipeline as db check
    console.print("[bold]Step 4: Validating schema after upgrade...[/bold]")
    run_readiness_checks(build_db_check_pipeline(), "post-upgrade validation")
    console.print("[green]Post-upgrade validation passed[/green]")
    console.print("[bold green]Database upgrade completed successfully![/bold green]")
