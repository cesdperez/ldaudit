"""Output formatting for feature flags using Rich library."""

from rich import box
from rich.table import Table
from rich.text import Text

from ld_audit.models import Flag


def format_date(timestamp_ms: int) -> str:
    """
    Format timestamp to YYYY-MM-DD.

    Args:
        timestamp_ms: Timestamp in milliseconds

    Returns:
        Formatted date string
    """
    import datetime

    from ld_audit.config import MILLISECONDS_TO_SECONDS

    return datetime.datetime.fromtimestamp(timestamp_ms / MILLISECONDS_TO_SECONDS).strftime("%Y-%m-%d")


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


def format_env_status(flag: Flag, include_parentheses: bool = True) -> str:
    """
    Format environment status as inline string with color codes.

    Args:
        flag: Flag object
        include_parentheses: Whether to wrap the result in parentheses

    Returns:
        Formatted string like "(prod: OFF, staging: ON, dev: ON)"
    """
    if not flag.environments:
        return "(no environments)" if include_parentheses else "no environments"

    env_parts = []
    for env_name in sorted(flag.environments.keys()):
        env = flag.environments[env_name]
        status = "ON" if env.is_on else "OFF"
        color = "green" if env.is_on else "red"
        env_parts.append(f"[{color}]{env_name}: {status}[/{color}]")

    result = ", ".join(env_parts)
    return f"({result})" if include_parentheses else result


def create_flags_table(flags: list[Flag], project: str, base_url: str) -> Table:
    """
    Create a Rich table for displaying flags with all environments shown inline.

    Args:
        flags: List of Flag objects
        project: LaunchDarkly project name
        base_url: LaunchDarkly base URL

    Returns:
        Rich Table object
    """
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Flag Key", style="cyan")
    table.add_column("Environments", style="magenta")
    table.add_column("Maintainer", style="yellow")
    table.add_column("Created", style="dim")
    table.add_column("Last Modified", style="dim")

    for flag in flags:
        flag_url = f"{base_url}/{project}/production/features/{flag.key}"
        flag_link = f"[link={flag_url}]{flag.key}[/link]"

        env_status = format_env_status(flag, include_parentheses=False)
        maintainer = flag.maintainer.first_name

        created = format_date(int(flag.creation_date.timestamp() * 1000))

        most_recent = flag.most_recent_modification
        modified = format_date(int(most_recent.timestamp() * 1000)) if most_recent else "N/A"

        table.add_row(flag_link, env_status, maintainer, created, modified)

    return table
