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


def get_maintainer_breakdown(
    all_flags: list[Flag],
    ready_to_archive_flags: list[Flag],
    inactive_flags: list[Flag],
) -> list[dict[str, int | str]]:
    """
    Get flag counts grouped by maintainer, sorted by total descending.

    Args:
        all_flags: List of all flags
        ready_to_archive_flags: List of ready to archive flags
        inactive_flags: List of inactive flags

    Returns:
        List of dicts with maintainer name and counts
    """
    ready_keys = {f.key for f in ready_to_archive_flags}
    inactive_keys = {f.key for f in inactive_flags}

    maintainer_counts: dict[str, dict[str, int]] = {}

    for flag in all_flags:
        name = flag.maintainer.first_name
        if name not in maintainer_counts:
            maintainer_counts[name] = {"total": 0, "ready": 0, "inactive": 0}

        maintainer_counts[name]["total"] += 1
        if flag.key in ready_keys:
            maintainer_counts[name]["ready"] += 1
        if flag.key in inactive_keys:
            maintainer_counts[name]["inactive"] += 1

    # Sort by total descending
    sorted_maintainers = sorted(maintainer_counts.items(), key=lambda x: x[1]["total"], reverse=True)

    return [
        {
            "maintainer": name,
            "total": counts["total"],
            "ready_to_archive": counts["ready"],
            "inactive": counts["inactive"],
        }
        for name, counts in sorted_maintainers
    ]


def _generate_flags_markdown_table(flags: list[Flag], project: str, base_url: str) -> str:
    """Generate a markdown table for a list of flags."""
    if not flags:
        return ""

    headers, rows = get_flags_data(flags, project, base_url)
    return to_markdown(headers, rows)


def generate_audit_report(
    all_flags: list[Flag],
    ready_to_archive_flags: list[Flag],
    inactive_flags: list[Flag],
    project: str,
    base_url: str,
    months: int,
    min_age_days: int,
    eval_window_days: int,
    version: str,
) -> str:
    """
    Generate a comprehensive audit report in markdown format.

    Args:
        all_flags: List of all active flags
        ready_to_archive_flags: List of flags ready to archive
        inactive_flags: List of inactive flags
        project: LaunchDarkly project name
        base_url: LaunchDarkly base URL
        months: Inactivity threshold in months
        min_age_days: Minimum age for ready-to-archive
        eval_window_days: Evaluation window for ready-to-archive
        version: Tool version string

    Returns:
        Complete markdown report string
    """
    import datetime

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp_str = now.strftime("%Y-%m-%d at %H:%M UTC")

    # Calculate statistics
    total_live = len(all_flags)
    permanent_count = len([f for f in all_flags if not f.temporary])
    temporary_count = len([f for f in all_flags if f.temporary])
    ready_count = len(ready_to_archive_flags)
    inactive_count = len(inactive_flags)

    # Build report sections
    sections = []

    # Header
    sections.append(f"# LaunchDarkly Feature Flags Audit - {date_str}")
    sections.append("")
    sections.append(f"Report generated with [ldaudit](https://github.com/cesdperez/ldaudit) v{version}")
    sections.append("")
    sections.append("```sh")
    sections.append("ldaudit audit")
    sections.append("```")
    sections.append("")

    # Summary
    sections.append("## Summary")
    sections.append("")
    sections.append("| Metric | Count |")
    sections.append("|--------|-------|")
    sections.append(f"| **Total live flags** | {total_live} |")
    sections.append(f"| Permanent flags | {permanent_count} |")
    sections.append(f"| Temporary flags | {temporary_count} |")
    sections.append(f"| **Ready to archive** | {ready_count} |")
    sections.append(f"| **Inactive ({months}+ months)** | {inactive_count} |")
    sections.append("")
    sections.append("---")
    sections.append("")

    # Flags by Maintainer
    sections.append("## Flags by Maintainer")
    sections.append("")
    maintainer_breakdown = get_maintainer_breakdown(all_flags, ready_to_archive_flags, inactive_flags)
    if maintainer_breakdown:
        sections.append("| Maintainer | Total | Ready to Archive | Inactive |")
        sections.append("|------------|-------|------------------|----------|")
        for row in maintainer_breakdown:
            sections.append(f"| {row['maintainer']} | {row['total']} | {row['ready_to_archive']} | {row['inactive']} |")
    else:
        sections.append("No flags found.")
    sections.append("")
    sections.append("---")
    sections.append("")

    # Ready to Archive Flags
    sections.append("## Ready to Archive Flags")
    sections.append("")
    sections.append("- Temporary (not permanent)")
    sections.append(f"- Older than {min_age_days} days")
    sections.append(f"- Not requested in the past {eval_window_days} days")
    sections.append("")
    sections.append("```sh")
    sections.append("ldaudit ready-to-archive")
    sections.append("```")
    sections.append("")
    if ready_to_archive_flags:
        sections.append(_generate_flags_markdown_table(ready_to_archive_flags, project, base_url))
    else:
        sections.append("No flags in this category.")
    sections.append("")
    sections.append("---")
    sections.append("")

    # Inactive Flags
    sections.append("## Inactive Flags")
    sections.append("")
    sections.append("- Temporary (not permanent)")
    sections.append(f"- Not modified in any environment for {months}+ months")
    sections.append("")
    sections.append("```sh")
    sections.append("ldaudit inactive")
    sections.append("```")
    sections.append("")
    if inactive_flags:
        sections.append(_generate_flags_markdown_table(inactive_flags, project, base_url))
    else:
        sections.append("No flags in this category.")
    sections.append("")
    sections.append("---")
    sections.append("")

    # All Flags (at the end for less verbosity)
    sections.append("## All Flags")
    sections.append("")
    sections.append("- All active (non-archived) feature flags")
    sections.append("")
    sections.append("```sh")
    sections.append("ldaudit list")
    sections.append("```")
    sections.append("")
    if all_flags:
        sections.append(_generate_flags_markdown_table(all_flags, project, base_url))
    else:
        sections.append("No flags in this category.")
    sections.append("")
    sections.append("---")
    sections.append("")

    # Footer
    sections.append(f"*Report generated on {timestamp_str}*")

    return "\n".join(sections)


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
