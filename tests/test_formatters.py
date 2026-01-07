import pytest

from ld_audit.formatters import (
    generate_audit_report,
    get_maintainer_breakdown,
    strip_rich_markup,
    to_json,
    to_markdown,
)


def test_strip_rich_markup():
    text = "[bold green]ON[/bold green]"
    assert strip_rich_markup(text) == "ON"

    text = "[red]OFF[/red] (staging)"
    assert strip_rich_markup(text) == "OFF (staging)"


def test_to_markdown():
    headers = ["Col1", "Col2"]
    rows = [
        [
            "Key1",
            "[green]ON[/green]",
            "John",
            "2023-01-01",
            "2023-01-02",
            "https://app.launchdarkly.com/test-project/production/features/Key1",
        ],
    ]

    markdown = to_markdown(headers, rows)

    assert "| Col1 | Col2 |" in markdown
    assert "| --- | --- |" in markdown
    assert (
        "| [Key1](https://app.launchdarkly.com/test-project/production/features/Key1) | ON | John | 2023-01-01 | 2023-01-02 |"
        in markdown
    )


def test_to_json():
    headers = ["Col1", "Col2"]
    rows = [
        [
            "Key1",
            "[green]ON[/green]",
            "John",
            "2023-01-01",
            "2023-01-02",
            "https://app.launchdarkly.com/test-project/production/features/Key1",
        ],
    ]

    json_str = to_json(headers, rows)
    import json

    data = json.loads(json_str)

    assert len(data) == 1
    assert data[0]["key"] == "Key1"
    assert data[0]["environments"] == "ON"
    assert data[0]["maintainer"] == "John"
    assert data[0]["url"] == "https://app.launchdarkly.com/test-project/production/features/Key1"


class TestGetMaintainerBreakdown:
    @pytest.fixture
    def sample_flags(self, sample_flag_data, dicts_to_flags):
        """Create sample flags for testing."""

        def _make_flags():
            flags_data = [
                sample_flag_data(key="john-flag-1", maintainer_first_name="John", temporary=True),
                sample_flag_data(key="john-flag-2", maintainer_first_name="John", temporary=True),
                sample_flag_data(key="john-flag-3", maintainer_first_name="John", temporary=False),
                sample_flag_data(key="jane-flag-1", maintainer_first_name="Jane", temporary=True),
            ]
            return dicts_to_flags(flags_data)

        return _make_flags

    def test_maintainer_breakdown_sorted_by_total_desc(self, sample_flags):
        """Test that maintainer breakdown is sorted by total count descending."""
        all_flags = sample_flags()
        ready_flags = []
        inactive_flags = []

        breakdown = get_maintainer_breakdown(all_flags, ready_flags, inactive_flags)

        assert len(breakdown) == 2
        # John has 3 flags, Jane has 1 - John should be first
        assert breakdown[0]["maintainer"] == "John"
        assert breakdown[0]["total"] == 3
        assert breakdown[1]["maintainer"] == "Jane"
        assert breakdown[1]["total"] == 1

    def test_maintainer_breakdown_counts_ready_and_inactive(self, sample_flags):
        """Test that ready and inactive counts are calculated correctly."""
        all_flags = sample_flags()
        # Mark the first two as ready to archive
        ready_flags = [all_flags[0], all_flags[1]]
        # Mark one as inactive
        inactive_flags = [all_flags[0]]

        breakdown = get_maintainer_breakdown(all_flags, ready_flags, inactive_flags)

        john_row = next(r for r in breakdown if r["maintainer"] == "John")
        assert john_row["ready_to_archive"] == 2
        assert john_row["inactive"] == 1

    def test_maintainer_breakdown_empty_flags(self):
        """Test breakdown with no flags."""
        breakdown = get_maintainer_breakdown([], [], [])
        assert breakdown == []


class TestGenerateAuditReport:
    def test_report_contains_all_sections(self, sample_flag_data, dicts_to_flags):
        """Test that report contains all expected sections."""
        flags = dicts_to_flags([sample_flag_data(key="test-flag")])

        report = generate_audit_report(
            all_flags=flags,
            ready_to_archive_flags=[],
            inactive_flags=[],
            project="test-project",
            base_url="https://app.launchdarkly.com",
            months=3,
            min_age_days=30,
            eval_window_days=7,
            version="0.1.0",
        )

        assert "# LaunchDarkly Feature Flags Audit" in report
        assert "## Summary" in report
        assert "## Flags by Maintainer" in report
        assert "## All Flags" in report
        assert "## Ready to Archive Flags" in report
        assert "## Inactive Flags" in report
        assert "ldaudit audit" in report
        assert "v0.1.0" in report

    def test_report_empty_sections_show_message(self, sample_flag_data, dicts_to_flags):
        """Test that empty sections show 'No flags' message."""
        flags = dicts_to_flags([sample_flag_data(key="test-flag", temporary=False)])

        report = generate_audit_report(
            all_flags=flags,
            ready_to_archive_flags=[],
            inactive_flags=[],
            project="test-project",
            base_url="https://app.launchdarkly.com",
            months=3,
            min_age_days=30,
            eval_window_days=7,
            version="0.1.0",
        )

        # Count occurrences of "No flags in this category."
        count = report.count("No flags in this category.")
        # Should appear twice: once for ready-to-archive, once for inactive
        assert count == 2

    def test_report_summary_stats(self, sample_flag_data, dicts_to_flags):
        """Test that summary stats are calculated correctly."""
        flags = dicts_to_flags(
            [
                sample_flag_data(key="temp-flag", temporary=True),
                sample_flag_data(key="perm-flag", temporary=False),
            ]
        )

        report = generate_audit_report(
            all_flags=flags,
            ready_to_archive_flags=[flags[0]],
            inactive_flags=[flags[0]],
            project="test-project",
            base_url="https://app.launchdarkly.com",
            months=3,
            min_age_days=30,
            eval_window_days=7,
            version="0.1.0",
        )

        assert "| **Total live flags** | 2 |" in report
        assert "| Permanent flags | 1 |" in report
        assert "| Temporary flags | 1 |" in report
        assert "| **Ready to archive** | 1 |" in report
        assert "| **Inactive (3+ months)** | 1 |" in report

    def test_report_date_format_is_iso(self, sample_flag_data, dicts_to_flags):
        """Test that the report uses ISO date format."""
        flags = dicts_to_flags([sample_flag_data(key="test-flag")])

        report = generate_audit_report(
            all_flags=flags,
            ready_to_archive_flags=[],
            inactive_flags=[],
            project="test-project",
            base_url="https://app.launchdarkly.com",
            months=3,
            min_age_days=30,
            eval_window_days=7,
            version="0.1.0",
        )

        # Check that the title contains ISO date format (YYYY-MM-DD)
        import re

        # Match pattern like "# LaunchDarkly Feature Flags Audit - 2026-01-07"
        assert re.search(r"# LaunchDarkly Feature Flags Audit - \d{4}-\d{2}-\d{2}", report)
