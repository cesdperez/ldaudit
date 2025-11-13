#!/usr/bin/env python3
import datetime
import os
from typing import Any

import requests
import typer
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ld_audit import VERSION
from ld_audit.cache import SimpleCache

load_dotenv()

app = typer.Typer(help="LaunchDarkly feature flag audit tool")
console = Console()

api_key = os.getenv("LD_API_KEY")

# Default constants
DEFAULT_BASE_URL = "https://app.launchdarkly.com"
DEFAULT_ENV_ORDER = "production,staging,dev"
DEFAULT_CACHE_TTL = 3600
DEFAULT_MAX_FILE_SIZE_MB = 5
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "dist",
    "build",
    "venv",
    "env",
    ".pytest_cache",
    "bin",
    "obj",
}


def get_env_value(flag: dict[str, Any], env: str, key: str = "on", default: Any = None) -> Any:
    """
    Safely get a value from a flag's environment configuration.

    Args:
        flag: Flag dictionary
        env: Environment name
        key: Key to retrieve from environment (default: 'on')
        default: Default value if not found

    Returns:
        Value from environment or default
    """
    return flag.get("environments", {}).get(env, {}).get(key, default)


def get_primary_env(flag: dict[str, Any], env_order: list[str]) -> str:
    """
    Get the primary environment for a flag, falling back if preferred environment doesn't exist.

    Args:
        flag: Flag dictionary
        env_order: Preferred environment order

    Returns:
        Name of the primary environment to use
    """
    environments = flag.get("environments", {})
    if not environments:
        return env_order[0] if env_order else "production"

    for env in env_order:
        if env in environments:
            return env

    return list(environments.keys())[0]


def fetch_all_live_flags(
    project: str, base_url: str, cache: SimpleCache, use_cache: bool = True, override_cache: bool = False
) -> dict[str, Any]:
    """
    Fetch all flags from LaunchDarkly API for a given project.

    Args:
        project: LaunchDarkly project name
        base_url: LaunchDarkly base URL
        cache: Cache instance
        use_cache: Whether to use cached data if available (default: True)
        override_cache: Force refresh from API and update cache (default: False)

    Returns:
        Dictionary containing flag data from API
    """
    if not api_key:
        console.print("[red]Error:[/red] LD_API_KEY not found in environment variables", style="bold")
        console.print("Set it in your .env file or export it: export LD_API_KEY=your-key")
        raise typer.Exit(code=1)

    if use_cache and not override_cache:
        cached_data = cache.get(project)
        if cached_data is not None:
            return cached_data

    url = f"{base_url}/api/v2/flags/{project}"
    headers = {"Authorization": api_key, "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if use_cache or override_cache:
            cache.set(project, data)

        return data
    except requests.exceptions.HTTPError:
        console.print(f"[red]Error:[/red] Failed to fetch flags (HTTP {response.status_code})", style="bold")
        if response.status_code == 401:
            console.print("Check your LD_API_KEY - it may be invalid or expired")
        elif response.status_code == 404:
            console.print(f"Project '{project}' not found")
        raise typer.Exit(code=1)
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error:[/red] Network error: {e}", style="bold")
        raise typer.Exit(code=1)


def filter_flags(
    items: list[dict[str, Any]],
    modified_before: datetime.datetime,
    is_archived: bool,
    is_temporary: bool,
    is_on: bool,
    env_order: list[str],
    maintainers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Filter flags based on criteria.

    Args:
        items: List of flag dictionaries
        modified_before: Datetime threshold for last modification
        is_archived: Filter for archived status
        is_temporary: Filter for temporary status
        is_on: Filter for on/off status in primary environment
        env_order: Preferred environment order
        maintainers: Optional list of maintainer first names to filter by

    Returns:
        Filtered list of flags
    """
    result = []

    for item in items:
        if item["archived"] != is_archived:
            continue
        if item["temporary"] != is_temporary:
            continue

        environments = item.get("environments", {})
        if not environments:
            continue

        all_envs_inactive = True
        for env_data in environments.values():
            last_modified = datetime.datetime.fromtimestamp(env_data.get("lastModified", 0) / 1000.0)
            if last_modified >= modified_before:
                all_envs_inactive = False
                break

        if not all_envs_inactive:
            continue

        primary_env = get_primary_env(item, env_order)
        if get_env_value(item, primary_env, "on") != is_on:
            continue

        if maintainers:
            maintainer_name = item.get("_maintainer", {}).get("firstName")
            if maintainer_name not in maintainers:
                continue

        result.append(item)

    return result


def _search_file_with_encoding(file_path: str, flag_keys: list[str], encoding: str) -> dict[str, list[tuple[str, int]]]:
    """
    Search a single file for flag keys with a specific encoding.

    Args:
        file_path: Path to file to search
        flag_keys: List of flag keys to search for
        encoding: Character encoding to use

    Returns:
        Dictionary mapping flag keys to list of (file_path, line_number) tuples
    """
    results = {key: [] for key in flag_keys}

    try:
        with open(file_path, encoding=encoding) as f:
            for line_num, line in enumerate(f, 1):
                for flag_key in flag_keys:
                    if f'"{flag_key}"' in line or f"'{flag_key}'" in line:
                        results[flag_key].append((file_path, line_num))
    except Exception:
        pass

    return {k: v for k, v in results.items() if v}


def search_directory(
    directory: str,
    flag_keys: list[str],
    extensions: list[str] | None = None,
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    exclude_dirs: set = None,
) -> dict[str, list[tuple[str, int]]]:
    """
    Search directory recursively for flag keys with exact string matching.

    Args:
        directory: Directory path to search
        flag_keys: List of flag keys to search for
        extensions: Optional list of file extensions to filter by
        max_file_size_mb: Maximum file size in MB to scan
        exclude_dirs: Set of directory names to exclude

    Returns:
        Dictionary mapping flag keys to list of (file_path, line_number) tuples
    """
    results = {key: [] for key in flag_keys}
    max_file_size = max_file_size_mb * 1024 * 1024
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if extensions:
                if not any(file.endswith(f".{ext}") for ext in extensions):
                    continue

            file_path = os.path.join(root, file)

            if os.path.getsize(file_path) > max_file_size:
                continue

            file_results = _search_file_with_encoding(file_path, flag_keys, "utf-8")
            if not file_results:
                file_results = _search_file_with_encoding(file_path, flag_keys, "latin-1")

            for key, locations in file_results.items():
                results[key].extend(locations)

    return {k: v for k, v in results.items() if v}


def format_date(timestamp_ms: int) -> str:
    """
    Format timestamp to YYYY-MM-DD.

    Args:
        timestamp_ms: Timestamp in milliseconds

    Returns:
        Formatted date string
    """
    return datetime.datetime.fromtimestamp(timestamp_ms / 1000.0).strftime("%Y-%m-%d")


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


def get_status_icon(is_on: bool) -> Text:
    """
    Get colored status icon.

    Args:
        is_on: Whether flag is on

    Returns:
        Rich Text object with colored status
    """
    if is_on:
        return Text("🟢 ON", style="green bold")
    else:
        return Text("🔴 OFF", style="red bold")


def get_inactive_flags(
    project: str,
    months: int,
    base_url: str,
    cache: SimpleCache,
    env_order: list[str],
    maintainers: list[str] | None = None,
    exclude_list: list[str] | None = None,
    use_cache: bool = True,
    override_cache: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Fetch and filter inactive flags from LaunchDarkly.

    Args:
        project: LaunchDarkly project name
        months: Inactivity threshold in months
        base_url: LaunchDarkly base URL
        cache: Cache instance
        env_order: Preferred environment order
        maintainers: Optional list of maintainer names to filter by
        exclude_list: Optional list of flag keys to exclude
        use_cache: Whether to use cache
        override_cache: Whether to override cache

    Returns:
        Tuple of (inactive_flags_off, inactive_flags_on)
    """
    flags = fetch_all_live_flags(project, base_url, cache, use_cache=use_cache, override_cache=override_cache)
    modified_before = datetime.datetime.now() - datetime.timedelta(days=months * 30)

    inactive_flags_off = filter_flags(
        items=flags["items"],
        modified_before=modified_before,
        is_archived=False,
        is_temporary=True,
        is_on=False,
        env_order=env_order,
        maintainers=maintainers,
    )

    inactive_flags_on = filter_flags(
        items=flags["items"],
        modified_before=modified_before,
        is_archived=False,
        is_temporary=True,
        is_on=True,
        env_order=env_order,
        maintainers=maintainers,
    )

    if exclude_list:
        inactive_flags_off = [f for f in inactive_flags_off if f["key"] not in exclude_list]
        inactive_flags_on = [f for f in inactive_flags_on if f["key"] not in exclude_list]

    return inactive_flags_off, inactive_flags_on


def create_flags_table(
    flags: list[dict[str, Any]], project: str, base_url: str, env_order: list[str], show_all_envs: bool = False
) -> Table:
    """
    Create a Rich table for displaying flags.

    Args:
        flags: List of flag dictionaries
        project: LaunchDarkly project name
        base_url: LaunchDarkly base URL
        env_order: Preferred environment order
        show_all_envs: Whether to show all environments

    Returns:
        Rich Table object
    """
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Status", style="bold", width=10)
    table.add_column("Flag Key", style="cyan")
    table.add_column("Maintainer", style="yellow")
    table.add_column("Created", style="dim")
    table.add_column("Last Modified", style="dim")

    if show_all_envs:
        table.add_column("Environments", style="magenta")

    for flag in flags:
        primary_env = get_primary_env(flag, env_order)
        is_on = get_env_value(flag, primary_env, "on", False)
        status = get_status_icon(is_on)
        flag_key = flag["key"]
        maintainer = flag.get("_maintainer", {}).get("firstName", "None")
        created = format_date(flag["creationDate"])
        modified = format_date(get_env_value(flag, primary_env, "lastModified", 0))

        flag_url = f"{base_url}/{project}/{primary_env}/features/{flag_key}"
        flag_link = f"[link={flag_url}]{flag_key}[/link]"

        if show_all_envs:
            env_statuses = []
            environments = flag.get("environments", {})

            ordered_envs = [e for e in env_order if e in environments] + [
                e for e in sorted(environments.keys()) if e not in env_order
            ]

            for env_name in ordered_envs:
                env_data = environments[env_name]
                env_status = "ON" if env_data.get("on") else "OFF"
                env_color = "green" if env_data.get("on") else "red"
                env_statuses.append(f"[{env_color}]{env_name}: {env_status}[/{env_color}]")

            env_text = "\n".join(env_statuses)
            table.add_row(status, flag_link, maintainer, created, modified, env_text)
        else:
            table.add_row(status, flag_link, maintainer, created, modified)

    return table


@app.command(name="list")
def list_flags(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
    env_order: str = typer.Option(DEFAULT_ENV_ORDER, "--env", help="Comma-separated environment priority order"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", help="LaunchDarkly base URL"),
    cache_ttl: int = typer.Option(DEFAULT_CACHE_TTL, "--cache-ttl", help="Cache TTL in seconds"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache for this run"),
    override_cache: bool = typer.Option(False, "--override-cache", help="Force refresh and rewrite cache"),
):
    """
    List all active feature flags for a project.

    Use --help for all options.
    """
    cache_instance = SimpleCache(ttl_seconds=cache_ttl)
    env_list = [e.strip() for e in env_order.split(",")]

    flags = fetch_all_live_flags(
        project, base_url, cache_instance, use_cache=not no_cache, override_cache=override_cache
    )
    items = flags["items"]

    if not items:
        console.print(f"[yellow]No flags found in project '{project}'[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"\n[bold]Feature Flags for Project:[/bold] [cyan]{project}[/cyan]")
    console.print(f"[dim]Total flags: {len(items)}[/dim]\n")

    table = create_flags_table(items, project, base_url, env_list, show_all_envs=True)
    console.print(table)
    console.print()


@app.command()
def inactive(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
    env_order: str = typer.Option(DEFAULT_ENV_ORDER, "--env", help="Comma-separated environment priority order"),
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
    cache_instance = SimpleCache(ttl_seconds=cache_ttl)
    env_list = [e.strip() for e in env_order.split(",")]
    maintainer_list = parse_comma_separated(maintainer)
    exclude_list = parse_comma_separated(exclude)

    inactive_flags_off, inactive_flags_on = get_inactive_flags(
        project=project,
        months=months,
        base_url=base_url,
        cache=cache_instance,
        env_order=env_list,
        maintainers=maintainer_list,
        exclude_list=exclude_list,
        use_cache=not no_cache,
        override_cache=override_cache,
    )

    total = len(inactive_flags_off) + len(inactive_flags_on)

    if total == 0:
        console.print("[green]✓ No inactive flags found![/green]")
        console.print(f"[dim]All temporary flags have been modified within the last {months} months.[/dim]")
        raise typer.Exit(code=0)

    console.print("\n[bold yellow]⚠️  Inactive Feature Flags[/bold yellow]")
    console.print(f"[dim]Flags not modified in any environment for {months}+ months[/dim]\n")
    console.print(f"[bold]Total inactive flags:[/bold] {total}\n")

    if inactive_flags_off:
        console.print(f"[bold red]🔴 Flags toggled OFF in primary environment:[/bold red] {len(inactive_flags_off)}")
        console.print("[dim]Suggested actions:[/dim]")
        console.print("  • Archive the flag and remove all code references")
        console.print("  • Or enable if still needed\n")

        table = create_flags_table(inactive_flags_off, project, base_url, env_list)
        console.print(table)
        console.print()

    if inactive_flags_on:
        console.print(f"[bold green]🟢 Flags toggled ON in primary environment:[/bold green] {len(inactive_flags_on)}")
        console.print("[dim]Suggested actions:[/dim]")
        console.print("  • Remove flag, keep the code path as default behavior")
        console.print("  • Or verify the flag is still needed\n")

        table = create_flags_table(inactive_flags_on, project, base_url, env_list)
        console.print(table)
        console.print()


@app.command()
def scan(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
    env_order: str = typer.Option(DEFAULT_ENV_ORDER, "--env", help="Comma-separated environment priority order"),
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

    cache_instance = SimpleCache(ttl_seconds=cache_ttl)
    env_list = [e.strip() for e in env_order.split(",")]
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

    inactive_flags_off, inactive_flags_on = get_inactive_flags(
        project=project,
        months=months,
        base_url=base_url,
        cache=cache_instance,
        env_order=env_list,
        maintainers=maintainer_list,
        exclude_list=exclude_list,
        use_cache=not no_cache,
        override_cache=override_cache,
    )

    all_inactive_flags = inactive_flags_off + inactive_flags_on
    flag_keys = [flag["key"] for flag in all_inactive_flags]

    console.print(f"[dim]Checking {len(flag_keys)} inactive flag(s) against codebase...[/dim]\n")

    search_results = search_directory(directory, flag_keys, ext_list, max_file_size_mb=max_file_size)

    flags_found = []
    for flag in all_inactive_flags:
        if flag["key"] in search_results:
            flags_found.append((flag, search_results[flag["key"]]))

    if not flags_found:
        console.print("[green]✓ No inactive flags found in codebase![/green]")
        console.print("[dim]All inactive flags have been cleaned up.[/dim]")
        raise typer.Exit(code=0)

    off_count = sum(1 for f, _ in flags_found if not get_env_value(f, get_primary_env(f, env_list), "on", False))
    on_count = len(flags_found) - off_count

    console.print(f"[bold yellow]Found {len(flags_found)} inactive flag(s) in codebase[/bold yellow]")
    console.print(f"[dim]({off_count} OFF, {on_count} ON)[/dim]\n")

    for flag, locations in flags_found:
        flag_key = flag["key"]
        primary_env = get_primary_env(flag, env_list)
        flag_url = f"{base_url}/{project}/{primary_env}/features/{flag_key}"
        maintainer = flag.get("_maintainer", {}).get("firstName", "None")
        created = format_date(flag["creationDate"])

        status = get_status_icon(get_env_value(flag, primary_env, "on", False))

        console.print(f"[bold cyan]{flag_key}[/bold cyan]", end=" ")
        console.print(status)
        console.print(f"  [dim]Maintainer:[/dim] {maintainer}")
        console.print(f"  [dim]Created:[/dim] {created}")
        console.print(f"  [dim]URL:[/dim] [link={flag_url}]{flag_url}[/link]")
        console.print("  [bold]Locations:[/bold]")

        for file_path, line_num in locations:
            console.print(f"    [yellow]{file_path}[/yellow]:[cyan]{line_num}[/cyan]")

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
    elif action == "list":
        import json

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

        import time

        current_time = time.time()

        for cache_file in sorted(cache_files):
            try:
                with open(cache_file) as f:
                    cached = json.load(f)
                    timestamp = cached.get("timestamp", 0)
                    project_name = cache_file.stem

                    cached_date = datetime.datetime.fromtimestamp(timestamp)
                    age_seconds = current_time - timestamp
                    age_minutes = int(age_seconds / 60)

                    if age_minutes < 60:
                        age_display = f"{age_minutes}m ago"
                    else:
                        age_hours = int(age_minutes / 60)
                        age_display = f"{age_hours}h ago"

                    expires_seconds = cache_instance.ttl_seconds - age_seconds
                    if expires_seconds > 0:
                        expires_minutes = int(expires_seconds / 60)
                        if expires_minutes < 60:
                            expires_display = f"in {expires_minutes}m"
                        else:
                            expires_hours = int(expires_minutes / 60)
                            expires_display = f"in {expires_hours}h"
                    else:
                        expires_display = "[red]expired[/red]"

                    table.add_row(project_name, cached_date.strftime("%Y-%m-%d %H:%M"), age_display, expires_display)
            except Exception:
                continue

        console.print(f"\n[bold]Cache Location:[/bold] {cache_dir}")
        console.print(f"[dim]TTL: {cache_instance.ttl_seconds // 60} minutes[/dim]\n")
        console.print(table)
        console.print()
    else:
        console.print(f"[red]Error:[/red] Unknown action '{action}'", style="bold")
        console.print("Valid actions: clear, list")
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", "-v", help="Show version and exit", is_flag=True),
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
