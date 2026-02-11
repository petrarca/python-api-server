"""Readiness check runner for CLI operations."""

import typer
from rich.console import Console

from api_server.readiness_pipeline import ReadinessPipeline

console = Console()


def run_readiness_checks(pipeline: ReadinessPipeline, operation_name: str) -> None:
    """Run readiness checks for any CLI operation.

    Executes the given pipeline and displays results using rich console.
    Exits with code 1 if any check fails.

    Args:
        pipeline: The readiness pipeline to execute
        operation_name: Name of the operation for logging

    Raises:
        typer.Exit: If any readiness check fails
    """
    console.print(f"[bold]Running {operation_name} readiness checks...[/bold]\n")

    pipeline.execute()

    # Check if all stages passed
    result = pipeline.last_result
    if not result or result.overall_status != "success":
        console.print(f"\n[red]{operation_name.title()} readiness checks failed![/red]\n")

        # Display failed checks
        if result:
            for stage_result in result.stage_results:
                for check_result in stage_result.check_results:
                    if check_result.status != "success":
                        console.print(f"  [{stage_result.stage_name}] {check_result.check_name}: {check_result.message}")

        console.print("\nFix the issues above and try again")
        raise typer.Exit(1)

    console.print(f"[green]All {operation_name} readiness checks passed![/green]\n")
