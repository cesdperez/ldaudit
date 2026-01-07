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


def strip_rich_markup(text: str) -> str:
    """
    Remove Rich markup tags from a string.

    Args:
        text: String with Rich markup

    Returns:
        Plain text string
    """
    from rich.text import Text

    return Text.from_markup(text).plain


def get_flags_data(flags: list[Flag], project: str, base_url: str) -> tuple[list[str], list[list[str]]]:
    """
    Get raw flag data for formatting.

    Args:
        flags: List of Flag objects
        project: LaunchDarkly project name
        base_url: LaunchDarkly base URL

    Returns:
        Tuple of (headers, rows)
    """
    headers = ["Flag Key", "Environments", "Maintainer", "Created", "Last Modified"]
    rows = []

    for flag in flags:
        flag_url = f"{base_url}/{project}/production/features/{flag.key}"
        # We store the base value and will format for the specific output later
        env_status = format_env_status(flag, include_parentheses=False)
        maintainer = flag.maintainer.first_name
        created = format_date(int(flag.creation_date.timestamp() * 1000))
        most_recent = flag.most_recent_modification
        modified = format_date(int(most_recent.timestamp() * 1000)) if most_recent else "N/A"

        rows.append([flag.key, env_status, maintainer, created, modified, flag_url])

    return headers, rows


def to_markdown(headers: list[str], rows: list[list[str]]) -> str:
    """
    Format data as a Markdown table.

    Args:
        headers: List of column headers
        rows: List of rows, each containing data and a URL at the end

    Returns:
        Markdown table string
    """
    # Stripping rich markup for markdown
    clean_rows = []
    for row in rows:
        # row: [key, envs, maintainer, created, modified, url]
        key, envs, maintainer, created, modified, url = row
        clean_envs = strip_rich_markup(envs)
        flag_link = f"[{key}]({url})"
        clean_rows.append([flag_link, clean_envs, maintainer, created, modified])

    # Build markdown table
    output = [f"| {' | '.join(headers)} |"]
    output.append(f"| {' | '.join(['---'] * len(headers))} |")

    for row in clean_rows:
        output.append(f"| {' | '.join(row)} |")

    return "\n".join(output)


def to_json(headers: list[str], rows: list[list[str]]) -> str:
    """
    Format data as JSON.

    Args:
        headers: List of column headers
        rows: List of rows

    Returns:
        JSON string
    """
    import json

    data = []
    for row in rows:
        # row: [key, envs, maintainer, created, modified, url]
        key, envs, maintainer, created, modified, url = row
        clean_envs = strip_rich_markup(envs)

        item = {
            "key": key,
            "environments": clean_envs,
            "maintainer": maintainer,
            "created": created,
            "last_modified": modified,
            "url": url,
        }
        data.append(item)

    return json.dumps(data, indent=2)


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
    headers, rows = get_flags_data(flags, project, base_url)

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column(headers[0], style="cyan")
    table.add_column(headers[1], style="magenta")
    table.add_column(headers[2], style="yellow")
    table.add_column(headers[3], style="dim")
    table.add_column(headers[4], style="dim")

    for row in rows:
        # row: [key, envs, maintainer, created, modified, url]
        key, envs, maintainer, created, modified, url = row
        flag_link = f"[link={url}]{key}[/link]"
        table.add_row(flag_link, envs, maintainer, created, modified)

    return table
