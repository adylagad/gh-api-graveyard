"""Console output utilities using rich library for beautiful CLI."""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.theme import Theme

# Custom theme for the CLI
custom_theme = Theme(
    {
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "bold cyan",
        "highlight": "bold magenta",
    }
)

console = Console(theme=custom_theme)


def print_success(message: str):
    """Print a success message in green."""
    console.print(f"✓ {message}", style="success")


def print_error(message: str):
    """Print an error message in red."""
    console.print(f"✗ {message}", style="error")


def print_warning(message: str):
    """Print a warning message in yellow."""
    console.print(f"⚠ {message}", style="warning")


def print_info(message: str):
    """Print an info message in cyan."""
    console.print(f"ℹ {message}", style="info")


def print_section(title: str):
    """Print a section header."""
    console.print(f"\n[bold]{title}[/bold]")
    console.print("─" * len(title))


def print_panel(content: str, title: Optional[str] = None, style: str = "info"):
    """Print content in a panel box."""
    console.print(Panel(content, title=title, border_style=style))


def create_results_table(endpoints: List[Dict[str, Any]], unused: List[Dict[str, Any]]) -> Table:
    """Create a formatted table for scan results."""
    table = Table(title="Scan Results", show_header=True, header_style="bold magenta")

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", justify="right", style="green")

    total_endpoints = len(endpoints)
    unused_count = len(unused)
    used_count = total_endpoints - unused_count
    unused_percentage = (unused_count / total_endpoints * 100) if total_endpoints > 0 else 0

    table.add_row("Total Endpoints", str(total_endpoints))
    table.add_row("Used Endpoints", f"[green]{used_count}[/green]")
    table.add_row("Unused Endpoints", f"[red]{unused_count}[/red]")
    table.add_row("Unused Percentage", f"[yellow]{unused_percentage:.1f}%[/yellow]")

    return table


def create_endpoints_table(endpoints: List[Dict[str, Any]], title: str = "Endpoints") -> Table:
    """Create a formatted table for endpoints list."""
    table = Table(title=title, show_header=True, header_style="bold cyan")

    table.add_column("Method", style="magenta", no_wrap=True)
    table.add_column("Path", style="cyan")
    table.add_column("Hits", justify="right", style="green")

    for endpoint in endpoints:
        method = endpoint.get("method", "?")
        path = endpoint.get("path", "?")
        hits = endpoint.get("hits", 0)

        # Color code by hits
        if hits == 0:
            hit_str = f"[red]{hits}[/red]"
        elif hits < 10:
            hit_str = f"[yellow]{hits}[/yellow]"
        else:
            hit_str = f"[green]{hits}[/green]"

        table.add_row(method, path, hit_str)

    return table


def create_history_table(scans: List[Dict[str, Any]]) -> Table:
    """Create a formatted table for scan history."""
    table = Table(title="Scan History", show_header=True, header_style="bold cyan")

    table.add_column("ID", style="magenta", no_wrap=True)
    table.add_column("Service", style="cyan")
    table.add_column("Date", style="white")
    table.add_column("Endpoints", justify="right", style="green")
    table.add_column("Unused", justify="right", style="red")

    for scan in scans:
        scan_id = str(scan.get("id", "?"))
        service = scan.get("service_name", "?")
        timestamp = scan.get("timestamp", "?")
        total = str(scan.get("total_endpoints", 0))
        unused = str(scan.get("unused_endpoints", 0))

        table.add_row(scan_id, service, timestamp, total, unused)

    return table


def create_trend_table(trend_data: List[Dict[str, Any]]) -> Table:
    """Create a formatted table for trend data."""
    table = Table(title="Trend Analysis", show_header=True, header_style="bold cyan")

    table.add_column("Date", style="white")
    table.add_column("Total", justify="right", style="cyan")
    table.add_column("Unused", justify="right", style="red")
    table.add_column("Change", justify="right")

    prev_unused = None
    for data in trend_data:
        date = data.get("date", "?")
        total = str(data.get("total_endpoints", 0))
        unused = data.get("unused_endpoints", 0)
        unused_str = str(unused)

        # Calculate change
        if prev_unused is not None:
            change = unused - prev_unused
            if change > 0:
                change_str = f"[red]+{change}[/red]"
            elif change < 0:
                change_str = f"[green]{change}[/green]"
            else:
                change_str = "[white]0[/white]"
        else:
            change_str = "[dim]-[/dim]"

        table.add_row(date, total, unused_str, change_str)
        prev_unused = unused

    return table


def create_cost_table(cost_data: Dict[str, Any]) -> Table:
    """Create a formatted table for cost analysis."""
    table = Table(title="Cost Analysis", show_header=True, header_style="bold green")

    table.add_column("Timeframe", style="cyan", no_wrap=True)
    table.add_column("Savings", justify="right", style="green")

    monthly = cost_data.get("monthly_savings", 0)
    annual = cost_data.get("annual_savings", 0)
    three_year = cost_data.get("three_year_savings", 0)

    table.add_row("Monthly", f"${monthly:.2f}")
    table.add_row("Annual", f"${annual:.2f}")
    table.add_row("3-Year", f"[bold]${three_year:.2f}[/bold]")

    return table


def get_spinner_progress():
    """Create a spinner progress indicator."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )
