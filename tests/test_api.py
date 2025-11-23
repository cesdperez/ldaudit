"""Tests for API integration functions."""

from unittest.mock import patch

import pytest
import responses

from ld_audit.api_client import LaunchDarklyAPIError, LaunchDarklyClient
from ld_audit.cache import SimpleCache
from ld_audit.config import DEFAULT_BASE_URL


@pytest.mark.integration
class TestLaunchDarklyClient:
    @responses.activate
    def test_get_all_flags_success(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test successful API fetch."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)

        response_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=response_data,
            status=200,
        )

        result = client.get_all_flags("test-project")

        assert len(result) > 0
        assert len(responses.calls) == 1
        assert responses.calls[0].request.headers["Authorization"] == "test-api-key"

    @responses.activate
    def test_get_all_flags_uses_cache(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that cached data is used when available."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        cached_data = mock_api_response()
        cache.set("test-project", cached_data)

        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)
        result = client.get_all_flags("test-project")

        assert len(result) > 0
        assert len(responses.calls) == 0

    @responses.activate
    def test_get_all_flags_bypasses_cache_when_disabled(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that cache is bypassed when enable_cache=False."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        old_data = {
            "items": [
                {
                    "key": "old-flag",
                    "archived": False,
                    "temporary": True,
                    "creationDate": 1000,
                    "environments": {},
                    "_maintainer": {"firstName": "John"},
                }
            ]
        }
        cache.set("test-project", old_data)

        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)

        new_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=new_data,
            status=200,
        )

        result = client.get_all_flags("test-project", enable_cache=False)

        assert len(result) > 0
        assert len(responses.calls) == 1

    @responses.activate
    def test_get_all_flags_force_refresh_updates_cache(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that force_refresh=True refreshes and updates cache."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        old_data = {
            "items": [
                {
                    "key": "old-flag",
                    "archived": False,
                    "temporary": True,
                    "creationDate": 1000,
                    "environments": {},
                    "_maintainer": {"firstName": "John"},
                }
            ]
        }
        cache.set("test-project", old_data)

        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)

        new_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=new_data,
            status=200,
        )

        result = client.get_all_flags("test-project", force_refresh=True)

        assert len(result) > 0
        cached = cache.get("test-project")
        assert cached == new_data
        assert len(responses.calls) == 1

    @responses.activate
    def test_get_all_flags_401_unauthorized(self, temp_cache_dir, monkeypatch):
        """Test 401 Unauthorized error handling."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        client = LaunchDarklyClient(api_key="invalid-key", base_url=DEFAULT_BASE_URL, cache=cache)

        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(LaunchDarklyAPIError) as exc_info:
            client.get_all_flags("test-project")

        assert exc_info.value.status_code == 401
        assert "Invalid or expired API key" in exc_info.value.message

    @responses.activate
    def test_get_all_flags_404_not_found(self, temp_cache_dir, monkeypatch):
        """Test 404 Not Found error handling."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)

        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/nonexistent-project",
            json={"error": "Not Found"},
            status=404,
        )

        with pytest.raises(LaunchDarklyAPIError) as exc_info:
            client.get_all_flags("nonexistent-project")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.message.lower()

    @responses.activate
    def test_get_all_flags_500_server_error(self, temp_cache_dir, monkeypatch):
        """Test 500 Server Error handling."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)

        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json={"error": "Internal Server Error"},
            status=500,
        )

        with pytest.raises(LaunchDarklyAPIError) as exc_info:
            client.get_all_flags("test-project")

        assert exc_info.value.status_code == 500

    def test_get_all_flags_network_error(self, temp_cache_dir, monkeypatch):
        """Test network error handling."""
        import requests

        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network timeout")

            with pytest.raises(LaunchDarklyAPIError) as exc_info:
                client.get_all_flags("test-project")

            assert "Network error" in exc_info.value.message

    @responses.activate
    def test_get_all_flags_with_custom_base_url(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test API fetch with custom base URL."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        custom_url = "https://custom.launchdarkly.com"
        client = LaunchDarklyClient(api_key="test-api-key", base_url=custom_url, cache=cache)

        response_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{custom_url}/api/v2/flags/test-project",
            json=response_data,
            status=200,
        )

        result = client.get_all_flags("test-project")

        assert len(result) > 0
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == f"{custom_url}/api/v2/flags/test-project"

    @responses.activate
    def test_get_all_flags_caches_api_response(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that API response is cached after fetch."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)

        response_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=response_data,
            status=200,
        )

        client.get_all_flags("test-project")

        cached_result = cache.get("test-project")
        assert cached_result == response_data

    @responses.activate
    def test_get_all_flags_no_cache_when_disabled(self, temp_cache_dir, monkeypatch, mock_api_response):
        """Test that response is not cached when enable_cache=False."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        cache = SimpleCache()
        client = LaunchDarklyClient(api_key="test-api-key", base_url=DEFAULT_BASE_URL, cache=cache)

        response_data = mock_api_response()
        responses.add(
            responses.GET,
            f"{DEFAULT_BASE_URL}/api/v2/flags/test-project",
            json=response_data,
            status=200,
        )

        client.get_all_flags("test-project", enable_cache=False)

        cached_result = cache.get("test-project")
        assert cached_result is None
