#!/usr/bin/env python3
import requests
from dotenv import load_dotenv
import os
import typer
import datetime
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text

load_dotenv()

VERSION = "2.0.0"
app = typer.Typer(help="LaunchDarkly feature flag audit tool")
console = Console()

# Global API key
api_key = os.getenv("LD_API_KEY")


def fetch_all_live_flags(project: str):
    """Fetch all flags from LaunchDarkly API for a given project."""
    if not api_key:
        console.print("[red]Error:[/red] LD_API_KEY not found in environment variables", style="bold")
        console.print("Set it in your .env file or export it: export LD_API_KEY=your-key")
        raise typer.Exit(code=1)

    url = f"https://app.launchdarkly.com/api/v2/flags/{project}"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]Error:[/red] Failed to fetch flags (HTTP {response.status_code})", style="bold")
        if response.status_code == 401:
            console.print("Check your LD_API_KEY - it may be invalid or expired")
        elif response.status_code == 404:
            console.print(f"Project '{project}' not found")
        raise typer.Exit(code=1)
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error:[/red] Network error: {e}", style="bold")
        raise typer.Exit(code=1)


def filter_flags(items, modified_before, is_archived, is_temporary, is_on, maintainers=None):
    """Filter flags based on criteria."""
    items = filter(lambda item: item['archived'] == is_archived, items)
    items = filter(lambda item: item['temporary'] == is_temporary, items)

    def is_inactive_in_all_environments(item):
        environments = item.get('environments', {})
        if not environments:
            return False

        for env_name, env_data in environments.items():
            last_modified = datetime.datetime.fromtimestamp(
                env_data.get('lastModified', 0) / 1000.0
            )
            if last_modified >= modified_before:
                return False

        return True

    items = filter(is_inactive_in_all_environments, items)
    items = filter(lambda item: item.get('environments', {}).get(
        'production', {}).get('on', None) == is_on, items)

    if maintainers:
        items = filter(lambda item: item.get('_maintainer', {}).get(
            'firstName', None) in maintainers, items)

    return list(items)


def search_directory(directory, flag_keys, extensions=None):
    """
    Search directory recursively for flag keys with exact string matching.
    Returns dict {flag_key: [(file_path, line_number), ...]}
    """
    results = {key: [] for key in flag_keys}
    exclude_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'dist', 'build', 'venv', 'env', '.pytest_cache', 'bin', 'obj'}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if extensions:
                if not any(file.endswith(f'.{ext}') for ext in extensions):
                    continue

            file_path = os.path.join(root, file)

            if os.path.getsize(file_path) > 1024 * 1024:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        for flag_key in flag_keys:
                            if f'"{flag_key}"' in line or f"'{flag_key}'" in line:
                                results[flag_key].append((file_path, line_num))
            except (UnicodeDecodeError, PermissionError, OSError):
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        for line_num, line in enumerate(f, 1):
                            for flag_key in flag_keys:
                                if f'"{flag_key}"' in line or f"'{flag_key}'" in line:
                                    results[flag_key].append((file_path, line_num))
                except Exception:
                    continue

    return {k: v for k, v in results.items() if v}


def format_date(timestamp_ms):
    """Format timestamp to YYYY-MM-DD."""
    return datetime.datetime.fromtimestamp(timestamp_ms / 1000.0).strftime('%Y-%m-%d')


def parse_comma_separated(values: Optional[List[str]]) -> Optional[List[str]]:
    """
    Parse comma-separated values from CLI options.
    Supports both --ext=cs,js and --ext=cs --ext=js
    """
    if not values:
        return None

    result = []
    for value in values:
        result.extend([v.strip() for v in value.split(',') if v.strip()])

    return result if result else None


def get_status_icon(is_on):
    """Get colored status icon."""
    if is_on:
        return Text("🟢 ON", style="green bold")
    else:
        return Text("🔴 OFF", style="red bold")


def create_flags_table(flags, project, show_all_envs=False):
    """Create a Rich table for displaying flags."""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Status", style="bold", width=10)
    table.add_column("Flag Key", style="cyan")
    table.add_column("Maintainer", style="yellow")
    table.add_column("Created", style="dim")
    table.add_column("Last Modified", style="dim")

    if show_all_envs:
        table.add_column("Environments", style="magenta")

    for flag in flags:
        status = get_status_icon(flag.get('environments', {}).get('production', {}).get('on', False))
        flag_key = flag['key']
        maintainer = flag.get('_maintainer', {}).get('firstName', 'None')
        created = format_date(flag['creationDate'])
        modified = format_date(flag.get('environments', {}).get('production', {}).get('lastModified', 0))

        flag_url = f"https://app.launchdarkly.com/{project}/production/features/{flag_key}"
        flag_link = f"[link={flag_url}]{flag_key}[/link]"

        if show_all_envs:
            env_statuses = []
            preferred_order = ['production', 'staging', 'dev']
            environments = flag.get('environments', {})

            ordered_envs = [e for e in preferred_order if e in environments] + \
                          [e for e in sorted(environments.keys()) if e not in preferred_order]

            for env_name in ordered_envs:
                env_data = environments[env_name]
                env_status = "ON" if env_data.get('on') else "OFF"
                env_color = "green" if env_data.get('on') else "red"
                env_statuses.append(f"[{env_color}]{env_name}: {env_status}[/{env_color}]")

            env_text = "\n".join(env_statuses)
            table.add_row(status, flag_link, maintainer, created, modified, env_text)
        else:
            table.add_row(status, flag_link, maintainer, created, modified)

    return table


@app.command(name="list")
def list_flags(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
):
    """
    List all active feature flags for a project.

    Example:
        ld-audit list --project=my-project
    """
    flags = fetch_all_live_flags(project)
    items = flags['items']

    if not items:
        console.print(f"[yellow]No flags found in project '{project}'[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"\n[bold]Feature Flags for Project:[/bold] [cyan]{project}[/cyan]")
    console.print(f"[dim]Total flags: {len(items)}[/dim]\n")

    table = create_flags_table(items, project, show_all_envs=True)
    console.print(table)
    console.print()


@app.command()
def inactive(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
    months: int = typer.Option(3, "--months", "-m", help="Inactivity threshold in months"),
    maintainer: Optional[List[str]] = typer.Option(None, "--maintainer", help="Filter by maintainer (comma-separated or repeated)"),
    exclude: Optional[List[str]] = typer.Option(None, "--exclude", help="Exclude specific flag keys (comma-separated or repeated)"),
):
    """
    List inactive temporary flags not modified in any environment for X months.

    Flags are considered inactive if they:
    - Are temporary (not permanent)
    - Are not archived
    - Haven't been modified in ANY environment for the specified period

    Example:
        ld-audit inactive --project=my-project --months=6
        ld-audit inactive --maintainer=john,jane
        ld-audit inactive --maintainer=john --maintainer=jane
        ld-audit inactive --exclude=known-flag,another-flag
        ld-audit inactive --exclude=known-flag --exclude=another-flag
    """
    flags = fetch_all_live_flags(project)
    modified_before = datetime.datetime.now() - datetime.timedelta(days=months*30)

    maintainer_list = parse_comma_separated(maintainer)
    exclude_list = parse_comma_separated(exclude)

    inactive_flags_off = filter_flags(
        items=flags['items'],
        modified_before=modified_before,
        is_archived=False,
        is_temporary=True,
        is_on=False,
        maintainers=maintainer_list,
    )

    inactive_flags_on = filter_flags(
        items=flags['items'],
        modified_before=modified_before,
        is_archived=False,
        is_temporary=True,
        is_on=True,
        maintainers=maintainer_list,
    )

    if exclude_list:
        inactive_flags_off = [f for f in inactive_flags_off if f['key'] not in exclude_list]
        inactive_flags_on = [f for f in inactive_flags_on if f['key'] not in exclude_list]

    total = len(inactive_flags_off) + len(inactive_flags_on)

    if total == 0:
        console.print(f"[green]✓ No inactive flags found![/green]")
        console.print(f"[dim]All temporary flags have been modified within the last {months} months.[/dim]")
        raise typer.Exit(code=0)

    console.print(f"\n[bold yellow]⚠️  Inactive Feature Flags[/bold yellow]")
    console.print(f"[dim]Flags not modified in any environment for {months}+ months[/dim]\n")
    console.print(f"[bold]Total inactive flags:[/bold] {total}\n")

    if inactive_flags_off:
        console.print(f"[bold red]🔴 Flags toggled OFF in production:[/bold red] {len(inactive_flags_off)}")
        console.print("[dim]Suggested actions:[/dim]")
        console.print("  • Archive the flag and remove all code references")
        console.print("  • Or enable in production if still needed\n")

        table = create_flags_table(inactive_flags_off, project)
        console.print(table)
        console.print()

    if inactive_flags_on:
        console.print(f"[bold green]🟢 Flags toggled ON in production:[/bold green] {len(inactive_flags_on)}")
        console.print("[dim]Suggested actions:[/dim]")
        console.print("  • Remove flag, keep the code path as default behavior")
        console.print("  • Or verify the flag is still needed\n")

        table = create_flags_table(inactive_flags_on, project)
        console.print(table)
        console.print()


@app.command()
def scan(
    project: str = typer.Option("default", "--project", "-p", help="LaunchDarkly project name"),
    directory: str = typer.Option(".", "--dir", "-d", help="Directory to scan"),
    months: int = typer.Option(3, "--months", "-m", help="Inactivity threshold in months"),
    ext: Optional[List[str]] = typer.Option(None, "--ext", help="File extensions to scan (comma-separated or repeated)"),
    maintainer: Optional[List[str]] = typer.Option(None, "--maintainer", help="Filter by maintainer (comma-separated or repeated)"),
    exclude: Optional[List[str]] = typer.Option(None, "--exclude", help="Exclude specific flag keys (comma-separated or repeated)"),
):
    """
    Scan a codebase for references to inactive flags.

    Searches for inactive flag keys in source files and reports their locations.

    Example:
        ld-audit scan --project=my-project --dir=/path/to/repo
        ld-audit scan --ext=cs,js,ts --dir=./src
        ld-audit scan --ext=cs --ext=js --ext=ts --dir=./src
        ld-audit scan --exclude=known-flag,another-flag
        ld-audit scan --exclude=known-flag --exclude=another-flag
    """
    if not os.path.isdir(directory):
        console.print(f"[red]Error:[/red] Directory '{directory}' does not exist", style="bold")
        raise typer.Exit(code=1)

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

    flags = fetch_all_live_flags(project)
    modified_before = datetime.datetime.now() - datetime.timedelta(days=months*30)

    inactive_flags_off = filter_flags(
        items=flags['items'],
        modified_before=modified_before,
        is_archived=False,
        is_temporary=True,
        is_on=False,
        maintainers=maintainer_list,
    )

    inactive_flags_on = filter_flags(
        items=flags['items'],
        modified_before=modified_before,
        is_archived=False,
        is_temporary=True,
        is_on=True,
        maintainers=maintainer_list,
    )

    all_inactive_flags = inactive_flags_off + inactive_flags_on

    if exclude_list:
        all_inactive_flags = [f for f in all_inactive_flags if f['key'] not in exclude_list]
    flag_keys = [flag['key'] for flag in all_inactive_flags]

    console.print(f"[dim]Checking {len(flag_keys)} inactive flag(s) against codebase...[/dim]\n")

    search_results = search_directory(directory, flag_keys, ext_list)

    flags_found = []
    for flag in all_inactive_flags:
        if flag['key'] in search_results:
            flags_found.append((flag, search_results[flag['key']]))

    if not flags_found:
        console.print("[green]✓ No inactive flags found in codebase![/green]")
        console.print("[dim]All inactive flags have been cleaned up.[/dim]")
        raise typer.Exit(code=0)

    off_count = sum(1 for f, _ in flags_found if not f['environments']['production']['on'])
    on_count = len(flags_found) - off_count

    console.print(f"[bold yellow]Found {len(flags_found)} inactive flag(s) in codebase[/bold yellow]")
    console.print(f"[dim]({off_count} OFF, {on_count} ON)[/dim]\n")

    for flag, locations in flags_found:
        flag_key = flag['key']
        flag_url = f"https://app.launchdarkly.com/{project}/production/features/{flag_key}"
        maintainer = flag.get('_maintainer', {}).get('firstName', 'None')
        created = format_date(flag['creationDate'])

        status = get_status_icon(flag['environments']['production']['on'])

        console.print(f"[bold cyan]{flag_key}[/bold cyan]", end=" ")
        console.print(status)
        console.print(f"  [dim]Maintainer:[/dim] {maintainer}")
        console.print(f"  [dim]Created:[/dim] {created}")
        console.print(f"  [dim]URL:[/dim] [link={flag_url}]{flag_url}[/link]")
        console.print(f"  [bold]Locations:[/bold]")

        for file_path, line_num in locations:
            console.print(f"    [yellow]{file_path}[/yellow]:[cyan]{line_num}[/cyan]")

        console.print()


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
        console.print(f"ld-audit version {VERSION}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print("[yellow]No command specified. Use --help for available commands.[/yellow]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
