"""Tests for CLI commands."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ld_audit.cli import app

runner = CliRunner()


@pytest.mark.integration
class TestListCommand:
    def test_list_command_success(self, mock_api_response, dicts_to_flags, monkeypatch):
        """Test successful list command execution."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            api_response = mock_api_response()
            mock_fetch.return_value = dicts_to_flags(api_response["items"])

            result = runner.invoke(app, ["list", "--project", "test-project"])

            assert result.exit_code == 0
            assert "Feature Flags for Project" in result.stdout
            assert "test-project" in result.stdout
            assert "Total flags live:" in result.stdout
            assert "Permanent flags:" in result.stdout
            assert "Temporary flags:" in result.stdout

    def test_list_command_with_no_flags(self, monkeypatch):
        """Test list command with no flags found."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = []

            result = runner.invoke(app, ["list", "--project", "empty-project"])

            assert result.exit_code == 0
            assert "No flags found" in result.stdout

    def test_list_command_with_maintainer_filter(self, sample_flag_data, dicts_to_flags, monkeypatch):
        """Test list command with maintainer filter."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        flags = [
            sample_flag_data(key="john-flag", maintainer_first_name="John"),
            sample_flag_data(key="jane-flag", maintainer_first_name="Jane"),
        ]

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags(flags)

            result = runner.invoke(app, ["list", "--project", "test-project", "--maintainer", "John"])

            assert result.exit_code == 0
            assert "john-flag" in result.stdout

    def test_list_command_with_exclude(self, sample_flag_data, dicts_to_flags, monkeypatch):
        """Test list command with exclude filter."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        flags = [
            sample_flag_data(key="keep-flag"),
            sample_flag_data(key="exclude-flag"),
        ]

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags(flags)

            result = runner.invoke(app, ["list", "--project", "test-project", "--exclude", "exclude-flag"])

            assert result.exit_code == 0
            assert "keep-flag" in result.stdout

    def test_list_command_no_cache_flag(self, mock_api_response, dicts_to_flags, monkeypatch):
        """Test list command with no-cache flag."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            api_response = mock_api_response()
            mock_fetch.return_value = dicts_to_flags(api_response["items"])

            result = runner.invoke(app, ["list", "--project", "test-project", "--no-cache"])

            assert result.exit_code == 0
            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args.kwargs
            assert call_kwargs["enable_cache"] is False

    def test_list_command_override_cache_flag(self, mock_api_response, dicts_to_flags, monkeypatch):
        """Test list command with override-cache flag."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            api_response = mock_api_response()
            mock_fetch.return_value = dicts_to_flags(api_response["items"])

            result = runner.invoke(app, ["list", "--project", "test-project", "--override-cache"])

            assert result.exit_code == 0
            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args.kwargs
            assert call_kwargs["force_refresh"] is True

    def test_list_command_json_format(self, mock_api_response, dicts_to_flags, monkeypatch):
        """Test list command with JSON format."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            api_response = mock_api_response()
            mock_fetch.return_value = dicts_to_flags(api_response["items"])

            result = runner.invoke(app, ["list", "--project", "test-project", "--format", "json"])

            assert result.exit_code == 0
            # Result should be a valid JSON list
            import json

            data = json.loads(result.stdout)
            assert isinstance(data, list)
            assert data[0]["key"] == api_response["items"][0]["key"]

    def test_list_command_markdown_export(self, mock_api_response, dicts_to_flags, monkeypatch):
        """Test list command with markdown export to file."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            api_response = mock_api_response()
            mock_fetch.return_value = dicts_to_flags(api_response["items"])

            with tempfile.TemporaryDirectory() as tmpdir:
                output_file = os.path.join(tmpdir, "results.md")
                result = runner.invoke(app, ["list", "--project", "test-project", "--output", output_file])

                assert result.exit_code == 0
                assert "Output saved to" in result.stdout
                assert os.path.exists(output_file)

                content = Path(output_file).read_text()
                assert "| Flag Key |" in content
                assert f"| [{api_response['items'][0]['key']}]" in content


@pytest.mark.integration
class TestInactiveCommand:
    def test_inactive_command_with_inactive_flags(
        self, inactive_flag, dict_to_flag, dicts_to_flags, sample_flag_data, monkeypatch
    ):
        """Test inactive command with inactive flags found."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

            with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                mock_get_inactive.return_value = [dict_to_flag(inactive_flag)]

                result = runner.invoke(app, ["inactive", "--project", "test-project"])

                assert result.exit_code == 0
                assert "Inactive Feature Flags" in result.stdout
                assert "inactive-flag" in result.stdout

    def test_inactive_command_with_no_inactive_flags(self, dicts_to_flags, sample_flag_data, monkeypatch):
        """Test inactive command with no inactive flags."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

            with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                mock_get_inactive.return_value = []

                result = runner.invoke(app, ["inactive", "--project", "test-project"])

                assert result.exit_code == 0
                assert "No inactive flags found" in result.stdout

    def test_inactive_command_custom_months(
        self, inactive_flag, dict_to_flag, dicts_to_flags, sample_flag_data, monkeypatch
    ):
        """Test inactive command with custom months threshold."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

            with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                mock_get_inactive.return_value = [dict_to_flag(inactive_flag)]

                result = runner.invoke(app, ["inactive", "--project", "test-project", "--months", "6"])

                assert result.exit_code == 0
                mock_get_inactive.assert_called_once()
                call_args = mock_get_inactive.call_args.args
                assert call_args[1] == 6

    def test_inactive_command_with_maintainer_filter(
        self, inactive_flag, dict_to_flag, dicts_to_flags, sample_flag_data, monkeypatch
    ):
        """Test inactive command with maintainer filter."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

            with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                mock_get_inactive.return_value = [dict_to_flag(inactive_flag)]

                result = runner.invoke(app, ["inactive", "--project", "test-project", "--maintainer", "John"])

                assert result.exit_code == 0
                mock_get_inactive.assert_called_once()
                call_args = mock_get_inactive.call_args.args
                assert call_args[2] == ["John"]

    def test_inactive_command_with_exclude(
        self, inactive_flag, dict_to_flag, dicts_to_flags, sample_flag_data, monkeypatch
    ):
        """Test inactive command with exclude filter."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

            with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                mock_get_inactive.return_value = [dict_to_flag(inactive_flag)]

                result = runner.invoke(app, ["inactive", "--project", "test-project", "--exclude", "some-flag"])

                assert result.exit_code == 0
                mock_get_inactive.assert_called_once()
                call_args = mock_get_inactive.call_args.args
                assert call_args[3] == ["some-flag"]


@pytest.mark.integration
class TestScanCommand:
    def test_scan_command_finds_inactive_flags_in_codebase(
        self, inactive_flag, dict_to_flag, dicts_to_flags, sample_flag_data, monkeypatch
    ):
        """Test scan command that finds inactive flags in codebase."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write('if client.variation("inactive-flag", user, False):\n')
                f.write('    print("Feature enabled")\n')

            with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
                mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

                with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                    mock_get_inactive.return_value = [dict_to_flag(inactive_flag)]

                    result = runner.invoke(app, ["scan", "--project", "test-project", "--dir", tmpdir])

                    assert result.exit_code == 0
                    assert "Found" in result.stdout
                    assert "inactive flag(s) in codebase" in result.stdout
                    assert "inactive-flag" in result.stdout

    def test_scan_command_no_inactive_flags_in_codebase(
        self, inactive_flag, dict_to_flag, dicts_to_flags, sample_flag_data, monkeypatch
    ):
        """Test scan command that finds no inactive flags in codebase."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write('print("No flags here")\n')

            with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
                mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

                with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                    mock_get_inactive.return_value = [dict_to_flag(inactive_flag)]

                    result = runner.invoke(app, ["scan", "--project", "test-project", "--dir", tmpdir])

                    assert result.exit_code == 0
                    assert "No inactive flags found in codebase" in result.stdout

    def test_scan_command_invalid_directory(self, monkeypatch):
        """Test scan command with invalid directory."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        result = runner.invoke(app, ["scan", "--project", "test-project", "--dir", "/nonexistent/directory"])

        assert result.exit_code == 1
        assert "does not exist" in result.stdout

    def test_scan_command_with_extension_filter(
        self, inactive_flag, dict_to_flag, dicts_to_flags, sample_flag_data, monkeypatch
    ):
        """Test scan command with extension filter."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = os.path.join(tmpdir, "test.py")
            js_file = os.path.join(tmpdir, "test.js")

            with open(py_file, "w") as f:
                f.write('if client.variation("inactive-flag", user, False):\n')

            with open(js_file, "w") as f:
                f.write('if (client.variation("inactive-flag", user, false)) {\n')

            with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
                mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

                with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                    mock_get_inactive.return_value = [dict_to_flag(inactive_flag)]

                    result = runner.invoke(app, ["scan", "--project", "test-project", "--dir", tmpdir, "--ext", "py"])

                    assert result.exit_code == 0
                    assert "test.py" in result.stdout or "inactive-flag" in result.stdout

    def test_scan_command_with_maintainer_and_exclude(
        self, inactive_flag, dicts_to_flags, sample_flag_data, monkeypatch
    ):
        """Test scan command with maintainer and exclude filters."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
                mock_fetch.return_value = dicts_to_flags([sample_flag_data()])

                with patch("ld_audit.flag_service.FlagService.get_inactive_flags") as mock_get_inactive:
                    mock_get_inactive.return_value = []

                    result = runner.invoke(
                        app,
                        [
                            "scan",
                            "--project",
                            "test-project",
                            "--dir",
                            tmpdir,
                            "--maintainer",
                            "John",
                            "--exclude",
                            "some-flag",
                        ],
                    )

                    assert result.exit_code == 0
                    mock_get_inactive.assert_called_once()
                    call_args = mock_get_inactive.call_args.args
                    assert call_args[2] == ["John"]
                    assert call_args[3] == ["some-flag"]


@pytest.mark.integration
class TestAuditCommand:
    def test_audit_command_generates_report(self, sample_flag_data, dicts_to_flags, monkeypatch):
        """Test audit command generates a markdown report."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        flags = [
            sample_flag_data(key="flag-1", temporary=True, maintainer_first_name="John"),
            sample_flag_data(key="flag-2", temporary=False, maintainer_first_name="Jane"),
        ]

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags(flags)

            with patch("ld_audit.api_client.LaunchDarklyClient.get_flag_statuses") as mock_statuses:
                mock_statuses.return_value = {}

                with tempfile.TemporaryDirectory() as tmpdir:
                    output_file = os.path.join(tmpdir, "audit-report.md")
                    result = runner.invoke(app, ["audit", "--project", "test-project", "--output", output_file])

                    assert result.exit_code == 0
                    assert "Audit report generated:" in result.stdout
                    assert os.path.exists(output_file)

                    content = Path(output_file).read_text()
                    # Check main sections exist
                    assert "# LaunchDarkly Feature Flags Audit" in content
                    assert "## Summary" in content
                    assert "## Flags by Maintainer" in content
                    assert "## All Flags" in content
                    assert "## Ready to Archive Flags" in content
                    assert "## Inactive Flags" in content
                    # Check command snippets
                    assert "ldaudit list" in content
                    assert "ldaudit ready-to-archive" in content
                    assert "ldaudit inactive" in content

    def test_audit_command_empty_sections(self, sample_flag_data, dicts_to_flags, monkeypatch):
        """Test audit command shows 'no flags' message for empty sections."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        # Create flags that won't be ready-to-archive or inactive
        one_week_ago = int(
            (__import__("datetime").datetime.now() - __import__("datetime").timedelta(days=7)).timestamp() * 1000
        )
        flags = [
            sample_flag_data(
                key="recent-flag",
                temporary=False,  # Permanent, won't be inactive or ready-to-archive
                environments={
                    "production": {"on": True, "lastModified": one_week_ago},
                },
            ),
        ]

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags(flags)

            with patch("ld_audit.api_client.LaunchDarklyClient.get_flag_statuses") as mock_statuses:
                mock_statuses.return_value = {}

                with tempfile.TemporaryDirectory() as tmpdir:
                    output_file = os.path.join(tmpdir, "audit-report.md")
                    result = runner.invoke(app, ["audit", "--project", "test-project", "--output", output_file])

                    assert result.exit_code == 0

                    content = Path(output_file).read_text()
                    # Should have "no flags" message for ready-to-archive and inactive
                    assert "No flags in this category." in content

    def test_audit_command_default_output_path(self, sample_flag_data, dicts_to_flags, monkeypatch):
        """Test audit command uses default filename when no output specified."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        flags = [sample_flag_data(key="flag-1")]

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags(flags)

            with patch("ld_audit.api_client.LaunchDarklyClient.get_flag_statuses") as mock_statuses:
                mock_statuses.return_value = {}

                with tempfile.TemporaryDirectory() as tmpdir:
                    # Change to temp directory to capture the default output file
                    original_cwd = os.getcwd()
                    os.chdir(tmpdir)
                    try:
                        result = runner.invoke(app, ["audit", "--project", "test-project"])

                        assert result.exit_code == 0
                        assert "Audit report generated:" in result.stdout
                        # Should contain audit-YYYY-MM-DD.md pattern
                        assert "audit-" in result.stdout
                        assert ".md" in result.stdout
                    finally:
                        os.chdir(original_cwd)

    def test_audit_command_with_maintainer_filter(self, sample_flag_data, dicts_to_flags, monkeypatch):
        """Test audit command with maintainer filter."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")

        flags = [
            sample_flag_data(key="john-flag", maintainer_first_name="John"),
            sample_flag_data(key="jane-flag", maintainer_first_name="Jane"),
        ]

        with patch("ld_audit.api_client.LaunchDarklyClient.get_all_flags") as mock_fetch:
            mock_fetch.return_value = dicts_to_flags(flags)

            with patch("ld_audit.api_client.LaunchDarklyClient.get_flag_statuses") as mock_statuses:
                mock_statuses.return_value = {}

                with tempfile.TemporaryDirectory() as tmpdir:
                    output_file = os.path.join(tmpdir, "audit-report.md")
                    result = runner.invoke(
                        app,
                        ["audit", "--project", "test-project", "--maintainer", "John", "--output", output_file],
                    )

                    assert result.exit_code == 0

                    content = Path(output_file).read_text()
                    # John's flags should be in the report
                    assert "john-flag" in content
                    # Jane's flags should be filtered out from All Flags
                    # (but might still appear in maintainer breakdown since that uses raw flags)


@pytest.mark.integration
class TestCacheCommand:
    def test_cache_list_command_empty(self, temp_cache_dir, monkeypatch):
        """Test cache list command with no cached projects."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        result = runner.invoke(app, ["cache", "list"])

        assert result.exit_code == 0
        assert "No cached projects found" in result.stdout

    def test_cache_list_command_with_projects(self, temp_cache_dir, monkeypatch):
        """Test cache list command with cached projects."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        from ld_audit.cache import SimpleCache

        cache = SimpleCache()
        cache.set("project-1", {"data": "test1"})
        cache.set("project-2", {"data": "test2"})

        result = runner.invoke(app, ["cache", "list"])

        assert result.exit_code == 0
        assert "project-1" in result.stdout
        assert "project-2" in result.stdout

    def test_cache_clear_command(self, temp_cache_dir, monkeypatch):
        """Test cache clear command."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        from ld_audit.cache import SimpleCache

        cache = SimpleCache()
        cache.set("project-1", {"data": "test1"})
        cache.set("project-2", {"data": "test2"})

        result = runner.invoke(app, ["cache", "clear"])

        assert result.exit_code == 0
        assert "cleared" in result.stdout.lower()

        cache_files = list(temp_cache_dir.glob("*.json"))
        assert len(cache_files) == 0


@pytest.mark.integration
class TestMainCallback:
    def test_version_flag(self):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "ld-audit version" in result.stdout or "version" in result.stdout.lower()

    def test_help_flag(self):
        """Test --help flag."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Usage" in result.stdout or "LaunchDarkly" in result.stdout
