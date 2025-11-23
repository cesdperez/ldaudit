#!/usr/bin/env python3
"""CLI commands for LaunchDarkly feature flag audit tool."""

import datetime
import json
import os
import time

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from ld_audit import VERSION
from ld_audit.api_client import LaunchDarklyAPIError, LaunchDarklyClient
from ld_audit.cache import SimpleCache
from ld_audit.config import DEFAULT_BASE_URL, DEFAULT_CACHE_TTL, DEFAULT_MAX_FILE_SIZE_MB, get_api_key
from ld_audit.file_search import CodebaseScanner
from ld_audit.flag_service import FlagService
from ld_audit.formatters import create_flags_table, format_date, format_env_status

app = typer.Typer(help="LaunchDarkly feature flag audit tool")
console = Console()


def parse_comma_separated(values: list[str] | None) -> list[str] | None:
    """
    Parse comma-separated values from CLI options.
    Supports both --ext=cs,js and --ext=cs --ext=js

    Args:
        values: List of values that may contain comma-separated items

    Returns:
        Flattened list of values or None if empty
    """
    if not values:
        return None

    result = []
    for value in values:
        result.extend([v.strip() for v in value.split(",") if v.strip()])

    return result if result else None


def handle_api_error(error: LaunchDarklyAPIError) -> None:
    """
    Handle API errors with user-friendly messages.

    Args:
        error: LaunchDarklyAPIError exception
    """
    console.print(f"[red]Error:[/red] {error.message}", style="bold")

    if error.status_code == 401:
        console.print("Check your LD_API_KEY - it may be invalid or expired")
    elif error.status_code == 404:
        console.print("Verify the project name is correct")

    raise typer.Exit(code=1)


@app.command(name="list")
def list_flags(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", help="LaunchDarkly base URL"),
    cache_ttl: int = typer.Option(DEFAULT_CACHE_TTL, "--cache-ttl", help="Cache TTL in seconds"),
    maintainer: list[str] | None = typer.Option(
        None, "--maintainer", help="Filter by maintainer first name (comma-separated or repeated)"
    ),
    exclude: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude specific flag keys (comma-separated or repeated)"
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache for this run"),
    override_cache: bool = typer.Option(False, "--override-cache", help="Force refresh and rewrite cache"),
):
    """
    List all active feature flags for a project.

    Use --help for all options.
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error:[/red] LD_API_KEY not found in environment variables", style="bold")
        console.print("Set it in your .env file or export it: export LD_API_KEY=your-key")
        raise typer.Exit(code=1)

    cache = SimpleCache(ttl_seconds=cache_ttl)
    client = LaunchDarklyClient(api_key=api_key, base_url=base_url, cache=cache)

    maintainer_list = parse_comma_separated(maintainer)
    exclude_list = parse_comma_separated(exclude)

    try:
        flags = client.get_all_flags(project, enable_cache=not no_cache, force_refresh=override_cache)
    except LaunchDarklyAPIError as e:
        handle_api_error(e)

    filtered_flags = FlagService.apply_common_filters(flags, maintainer_list, exclude_list)

    if not filtered_flags:
        console.print(f"[yellow]No flags found in project '{project}'[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"\n[bold]Feature Flags for Project:[/bold] [cyan]{project}[/cyan]")
    console.print(f"[dim]Total flags: {len(filtered_flags)}[/dim]\n")

    table = create_flags_table(filtered_flags, project, base_url)
    console.print(table)
    console.print()


@app.command()
def inactive(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
    months: int = typer.Option(3, "--months", "-m", help="Inactivity threshold in months"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", help="LaunchDarkly base URL"),
    cache_ttl: int = typer.Option(DEFAULT_CACHE_TTL, "--cache-ttl", help="Cache TTL in seconds"),
    maintainer: list[str] | None = typer.Option(
        None, "--maintainer", help="Filter by maintainer (comma-separated or repeated)"
    ),
    exclude: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude specific flag keys (comma-separated or repeated)"
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache for this run"),
    override_cache: bool = typer.Option(False, "--override-cache", help="Force refresh and rewrite cache"),
):
    """
    List inactive temporary flags not modified in any environment for X months.

    Use --help for all options.
    """
    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error:[/red] LD_API_KEY not found in environment variables", style="bold")
        console.print("Set it in your .env file or export it: export LD_API_KEY=your-key")
        raise typer.Exit(code=1)

    cache = SimpleCache(ttl_seconds=cache_ttl)
    client = LaunchDarklyClient(api_key=api_key, base_url=base_url, cache=cache)

    maintainer_list = parse_comma_separated(maintainer)
    exclude_list = parse_comma_separated(exclude)

    try:
        flags = client.get_all_flags(project, enable_cache=not no_cache, force_refresh=override_cache)
    except LaunchDarklyAPIError as e:
        handle_api_error(e)

    inactive_flags = FlagService.get_inactive_flags(flags, months, maintainer_list, exclude_list)

    if not inactive_flags:
        console.print("[green]✓ No inactive flags found![/green]")
        console.print(f"[dim]All temporary flags have been modified within the last {months} months.[/dim]")
        raise typer.Exit(code=0)

    console.print("\n[bold yellow]⚠️  Inactive Feature Flags[/bold yellow]")
    console.print(f"[dim]Flags not modified in any environment for {months}+ months[/dim]\n")
    console.print(f"[bold]Total inactive flags:[/bold] {len(inactive_flags)}\n")

    table = create_flags_table(inactive_flags, project, base_url)
    console.print(table)
    console.print()


@app.command()
def scan(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
    directory: str = typer.Option(".", "--dir", "-d", help="Directory to scan"),
    months: int = typer.Option(3, "--months", "-m", help="Inactivity threshold in months"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", help="LaunchDarkly base URL"),
    cache_ttl: int = typer.Option(DEFAULT_CACHE_TTL, "--cache-ttl", help="Cache TTL in seconds"),
    max_file_size: int = typer.Option(DEFAULT_MAX_FILE_SIZE_MB, "--max-file-size", help="Max file size in MB to scan"),
    ext: list[str] | None = typer.Option(None, "--ext", help="File extensions to scan (comma-separated or repeated)"),
    maintainer: list[str] | None = typer.Option(
        None, "--maintainer", help="Filter by maintainer (comma-separated or repeated)"
    ),
    exclude: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude specific flag keys (comma-separated or repeated)"
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache for this run"),
    override_cache: bool = typer.Option(False, "--override-cache", help="Force refresh and rewrite cache"),
):
    """
    Scan a codebase for references to inactive flags.

    Use --help for all options.
    """
    if not os.path.isdir(directory):
        console.print(f"[red]Error:[/red] Directory '{directory}' does not exist", style="bold")
        raise typer.Exit(code=1)

    api_key = get_api_key()
    if not api_key:
        console.print("[red]Error:[/red] LD_API_KEY not found in environment variables", style="bold")
        console.print("Set it in your .env file or export it: export LD_API_KEY=your-key")
        raise typer.Exit(code=1)

    cache = SimpleCache(ttl_seconds=cache_ttl)
    client = LaunchDarklyClient(api_key=api_key, base_url=base_url, cache=cache)

    ext_list = parse_comma_separated(ext)
    maintainer_list = parse_comma_separated(maintainer)
    exclude_list = parse_comma_separated(exclude)

    abs_dir = os.path.abspath(directory)
    console.print(f"\n[bold]Scanning directory:[/bold] [cyan]{abs_dir}[/cyan]")

    if ext_list:
        extensions_display = ", ".join([f".{e}" for e in ext_list])
        console.print(f"[bold]File extensions:[/bold] {extensions_display}")
    else:
        console.print("[dim]Scanning all file types[/dim]")

    if exclude_list:
        exclusions_display = ", ".join(exclude_list)
        console.print(f"[bold]Excluding flags:[/bold] {exclusions_display}")

    console.print()

    try:
        flags = client.get_all_flags(project, enable_cache=not no_cache, force_refresh=override_cache)
    except LaunchDarklyAPIError as e:
        handle_api_error(e)

    inactive_flags = FlagService.get_inactive_flags(flags, months, maintainer_list, exclude_list)
    flag_keys = [flag.key for flag in inactive_flags]

    console.print(f"[dim]Checking {len(flag_keys)} inactive flag(s) against codebase...[/dim]\n")

    scanner = CodebaseScanner(max_file_size_mb=max_file_size)
    search_results = scanner.search_directory(directory, flag_keys, ext_list)

    flags_found = [(flag, search_results[flag.key]) for flag in inactive_flags if flag.key in search_results]

    if not flags_found:
        console.print("[green]✓ No inactive flags found in codebase![/green]")
        console.print("[dim]All inactive flags have been cleaned up.[/dim]")
        raise typer.Exit(code=0)

    console.print(f"[bold yellow]Found {len(flags_found)} inactive flag(s) in codebase[/bold yellow]\n")

    for flag, locations in flags_found:
        flag_url = f"{base_url}/{project}/production/features/{flag.key}"
        created = format_date(int(flag.creation_date.timestamp() * 1000))
        env_status = format_env_status(flag)

        console.print(f"[bold cyan]{flag.key}[/bold cyan] {env_status}")
        console.print(f"  [dim]Maintainer:[/dim] {flag.maintainer.first_name}")
        console.print(f"  [dim]Created:[/dim] {created}")
        console.print(f"  [dim]URL:[/dim] [link={flag_url}]{flag_url}[/link]")
        console.print("  [bold]Locations:[/bold]")

        for location in locations:
            console.print(f"    [yellow]{location.file_path}[/yellow]:[cyan]{location.line_number}[/cyan]")

        console.print()


@app.command(name="cache")
def cache_cmd(
    action: str = typer.Argument(..., help="Action to perform: 'clear' or 'list'"),
    cache_ttl: int = typer.Option(DEFAULT_CACHE_TTL, "--cache-ttl", help="Cache TTL in seconds (for list display)"),
):
    """
    Manage the local cache.

    Use --help for all options.
    """
    cache_instance = SimpleCache(ttl_seconds=cache_ttl)

    if action == "clear":
        cache_instance.clear_all()
        console.print("[green]✓ Cache cleared successfully[/green]")
        return

    if action == "list":
        _display_cache_list(cache_instance)
        return

    console.print(f"[red]Error:[/red] Unknown action '{action}'", style="bold")
    console.print("Valid actions: clear, list")
    raise typer.Exit(code=1)


def _display_cache_list(cache_instance: SimpleCache) -> None:
    """Display list of cached projects."""
    cache_dir = cache_instance.cache_dir
    if not cache_dir.exists():
        console.print("[yellow]No cache directory found[/yellow]")
        raise typer.Exit(code=0)

    cache_files = list(cache_dir.glob("*.json"))
    if not cache_files:
        console.print("[yellow]No cached projects found[/yellow]")
        raise typer.Exit(code=0)

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Project", style="cyan")
    table.add_column("Cached", style="yellow")
    table.add_column("Age", style="dim")
    table.add_column("Expires", style="dim")

    current_time = time.time()

    for cache_file in sorted(cache_files):
        row_data = _get_cache_row_data(cache_file, current_time, cache_instance.ttl_seconds)
        if row_data:
            table.add_row(*row_data)

    console.print(f"\n[bold]Cache Location:[/bold] {cache_dir}")
    console.print(f"[dim]TTL: {cache_instance.ttl_seconds // 60} minutes[/dim]\n")
    console.print(table)
    console.print()


def _get_cache_row_data(cache_file, current_time: float, ttl_seconds: int) -> tuple[str, str, str, str] | None:
    """Get formatted cache row data or None if file can't be read."""
    try:
        with open(cache_file) as f:
            cached = json.load(f)
            timestamp = cached.get("timestamp", 0)
            project_name = cache_file.stem

            cached_date = datetime.datetime.fromtimestamp(timestamp)
            age_seconds = current_time - timestamp
            age_display = _format_time_duration(age_seconds)

            expires_seconds = ttl_seconds - age_seconds
            expires_display = _format_expiry(expires_seconds)

            return (project_name, cached_date.strftime("%Y-%m-%d %H:%M"), age_display, expires_display)
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _format_time_duration(seconds: float) -> str:
    """Format time duration in human-readable format."""
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"{minutes}m ago"
    else:
        hours = int(minutes / 60)
        return f"{hours}h ago"


def _format_expiry(expires_seconds: float) -> str:
    """Format expiry time in human-readable format."""
    if expires_seconds <= 0:
        return "[red]expired[/red]"

    expires_minutes = int(expires_seconds / 60)
    if expires_minutes < 60:
        return f"in {expires_minutes}m"
    else:
        expires_hours = int(expires_minutes / 60)
        return f"in {expires_hours}h"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", "-v", help="Show version and exit"),
):
    """
    LaunchDarkly Feature Flag Audit Tool

    Identify inactive temporary flags and find their references in your codebase.
    """
    if version:
        console.print(f"ldaudit version {VERSION}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print("[yellow]No command specified. Use --help for available commands.[/yellow]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
