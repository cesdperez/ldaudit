"""Tests for API integration functions."""

from unittest.mock import patch

import pytest
import responses
import typer

from ld_audit.cache import SimpleCache
from ld_audit.cli import DEFAULT_BASE_URL


@pytest.mark.integration
class TestFetchAllLiveFlags:
    @responses.activate
    def test_fetch_all_live_flags_success(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test successful API fetch."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        # Reload cli module to pick up new env var
        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        response_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=response_data,
            status=200,
        )

        result = cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache)

        assert result == response_data
        assert len(responses.calls) == 1
        assert responses.calls[0].request.headers["Authorization"] == "test-api-key"

    @responses.activate
    def test_fetch_all_live_flags_uses_cache(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that cached data is used when available."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()
        cached_data = mock_api_response()
        cache.set("test-project", cached_data)

        result = cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache)

        assert result == cached_data
        assert len(responses.calls) == 0

    @responses.activate
    def test_fetch_all_live_flags_bypasses_cache_when_disabled(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that cache is bypassed when enable_cache=False."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()
        old_data = {"items": [{"key": "old-flag"}]}
        cache.set("test-project", old_data)

        new_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=new_data,
            status=200,
        )

        result = cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache, enable_cache=False)

        assert result == new_data
        assert len(responses.calls) == 1

    @responses.activate
    def test_fetch_all_live_flags_force_refresh_updates_cache(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that force_refresh=True refreshes and updates cache."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()
        old_data = {"items": [{"key": "old-flag"}]}
        cache.set("test-project", old_data)

        new_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=new_data,
            status=200,
        )

        result = cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache, force_refresh=True)

        assert result == new_data
        assert cache.get("test-project") == new_data
        assert len(responses.calls) == 1

    def test_fetch_all_live_flags_missing_api_key(self, temp_cache_dir, monkeypatch):
        """Test that missing API key raises error."""
        monkeypatch.delenv("LD_API_KEY", raising=False)
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", None)

        cache = SimpleCache()

        with pytest.raises(typer.Exit) as exc_info:
            cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache)

        assert exc_info.value.exit_code == 1

    @responses.activate
    def test_fetch_all_live_flags_401_unauthorized(self, temp_cache_dir, monkeypatch):
        """Test 401 Unauthorized error handling."""
        monkeypatch.setenv("LD_API_KEY", "invalid-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "invalid-key")

        cache = SimpleCache()

        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(typer.Exit) as exc_info:
            cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache)

        assert exc_info.value.exit_code == 1

    @responses.activate
    def test_fetch_all_live_flags_404_not_found(self, temp_cache_dir, monkeypatch):
        """Test 404 Not Found error handling."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/nonexistent-project",
            json={"error": "Not Found"},
            status=404,
        )

        with pytest.raises(typer.Exit) as exc_info:
            cli_module.fetch_all_live_flags("nonexistent-project", DEFAULT_BASE_URL, cache)

        assert exc_info.value.exit_code == 1

    @responses.activate
    def test_fetch_all_live_flags_500_server_error(self, temp_cache_dir, monkeypatch):
        """Test 500 Server Error handling."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json={"error": "Internal Server Error"},
            status=500,
        )

        with pytest.raises(typer.Exit) as exc_info:
            cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache)

        assert exc_info.value.exit_code == 1

    def test_fetch_all_live_flags_network_error(self, temp_cache_dir, monkeypatch):
        """Test network error handling."""
        import requests

        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network timeout")

            with pytest.raises(typer.Exit) as exc_info:
                cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache)

            assert exc_info.value.exit_code == 1

    @responses.activate
    def test_fetch_all_live_flags_with_custom_base_url(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test API fetch with custom base URL."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()
        custom_url = "https://custom.launchdarkly.com"

        response_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{custom_url}/api/v2/flags/test-project",
            json=response_data,
            status=200,
        )

        result = cli_module.fetch_all_live_flags("test-project", custom_url, cache)

        assert result == response_data
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == f"{custom_url}/api/v2/flags/test-project"

    @responses.activate
    def test_fetch_all_live_flags_caches_api_response(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that API response is cached after fetch."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        response_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=response_data,
            status=200,
        )

        cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache)

        cached_result = cache.get("test-project")
        assert cached_result == response_data

    @responses.activate
    def test_fetch_all_live_flags_no_cache_when_disabled(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that response is not cached when enable_cache=False."""
        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        response_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=response_data,
            status=200,
        )

        cli_module.fetch_all_live_flags("test-project", DEFAULT_BASE_URL, cache, enable_cache=False)

        cached_result = cache.get("test-project")
        assert cached_result is None
