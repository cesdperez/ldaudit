"""Tests for the cache module."""

import json
import time
from pathlib import Path

import pytest

from ld_audit.cache import SimpleCache


@pytest.mark.unit
class TestSimpleCacheInit:
    def test_init_default_ttl(self, temp_cache_dir, monkeypatch):
        """Test cache initialization with default TTL."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()
        assert cache.ttl_seconds == 3600
        assert cache.cache_dir.exists()

    def test_init_custom_ttl(self, temp_cache_dir, monkeypatch):
        """Test cache initialization with custom TTL."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache(ttl_seconds=7200)
        assert cache.ttl_seconds == 7200

    def test_init_creates_cache_dir(self, temp_directory, monkeypatch):
        """Test that cache directory is created if it doesn't exist."""
        cache_dir = temp_directory / "new_cache"
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: cache_dir)
        cache = SimpleCache()
        assert cache.cache_dir.exists()
        assert cache.cache_dir.is_dir()


@pytest.mark.unit
class TestGetCacheFile:
    def test_get_cache_file_simple_key(self, temp_cache_dir, monkeypatch):
        """Test cache file path generation for simple key."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()
        cache_file = cache._get_cache_file("my-project")
        assert cache_file == cache.cache_dir / "my-project.json"

    def test_get_cache_file_sanitizes_forward_slash(self, temp_cache_dir, monkeypatch):
        """Test that forward slashes in keys are sanitized."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()
        cache_file = cache._get_cache_file("org/project")
        assert cache_file == cache.cache_dir / "org_project.json"

    def test_get_cache_file_sanitizes_backslash(self, temp_cache_dir, monkeypatch):
        """Test that backslashes in keys are sanitized."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()
        cache_file = cache._get_cache_file("org\\project")
        assert cache_file == cache.cache_dir / "org_project.json"


@pytest.mark.unit
class TestCacheGet:
    def test_get_returns_none_for_missing_file(self, temp_cache_dir, monkeypatch):
        """Test that get returns None when cache file doesn't exist."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_get_returns_valid_cached_data(self, temp_cache_dir, monkeypatch):
        """Test retrieving valid cached data."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache(ttl_seconds=3600)

        test_data = {"flags": [{"key": "test-flag"}]}
        cache.set("test-project", test_data)

        result = cache.get("test-project")
        assert result == test_data

    def test_get_returns_none_for_expired_data(self, temp_cache_dir, monkeypatch):
        """Test that get returns None for expired cache."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache(ttl_seconds=1)

        test_data = {"flags": [{"key": "test-flag"}]}
        cache.set("test-project", test_data)

        time.sleep(1.1)

        result = cache.get("test-project")
        assert result is None

    def test_get_handles_invalid_json(self, temp_cache_dir, monkeypatch):
        """Test that get returns None when JSON is invalid."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache_file = cache._get_cache_file("corrupt")
        cache_file.write_text("not valid json{{{")

        result = cache.get("corrupt")
        assert result is None

    def test_get_handles_missing_timestamp(self, temp_cache_dir, monkeypatch):
        """Test that get returns None when timestamp is missing."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache_file = cache._get_cache_file("no-timestamp")
        cache_file.write_text('{"data": {"key": "value"}}')

        result = cache.get("no-timestamp")
        assert result is None

    def test_get_handles_missing_data_key(self, temp_cache_dir, monkeypatch):
        """Test that get returns None when data key is missing."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache_file = cache._get_cache_file("no-data")
        cache_file.write_text(f'{{"timestamp": {time.time()}}}')

        result = cache.get("no-data")
        assert result is None

    def test_get_handles_os_error(self, temp_cache_dir, monkeypatch):
        """Test that get returns None when file read fails."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache_file = cache._get_cache_file("test")
        cache_file.write_text('{"timestamp": 123, "data": {}}')
        cache_file.chmod(0o000)

        try:
            result = cache.get("test")
            assert result is None
        finally:
            cache_file.chmod(0o644)


@pytest.mark.unit
class TestCacheSet:
    def test_set_creates_cache_file(self, temp_cache_dir, monkeypatch):
        """Test that set creates a cache file."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        test_data = {"key": "value"}
        cache.set("test-project", test_data)

        cache_file = cache._get_cache_file("test-project")
        assert cache_file.exists()

    def test_set_stores_data_with_timestamp(self, temp_cache_dir, monkeypatch):
        """Test that set stores data with timestamp."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        test_data = {"key": "value"}
        before_time = time.time()
        cache.set("test-project", test_data)
        after_time = time.time()

        cache_file = cache._get_cache_file("test-project")
        with open(cache_file) as f:
            cached = json.load(f)

        assert "timestamp" in cached
        assert "data" in cached
        assert cached["data"] == test_data
        assert before_time <= cached["timestamp"] <= after_time

    def test_set_overwrites_existing_cache(self, temp_cache_dir, monkeypatch):
        """Test that set overwrites existing cache."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache.set("test-project", {"old": "data"})
        cache.set("test-project", {"new": "data"})

        result = cache.get("test-project")
        assert result == {"new": "data"}

    def test_set_handles_os_error_gracefully(self, temp_cache_dir, monkeypatch):
        """Test that set handles OS errors gracefully (doesn't raise)."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache.cache_dir.chmod(0o444)

        try:
            cache.set("test-project", {"key": "value"})
        finally:
            cache.cache_dir.chmod(0o755)

    def test_set_stores_complex_data(self, temp_cache_dir, monkeypatch):
        """Test that set can store complex nested data structures."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        complex_data = {
            "items": [
                {"key": "flag-1", "environments": {"prod": {"on": True}}},
                {"key": "flag-2", "environments": {"staging": {"on": False}}},
            ],
            "totalCount": 2,
        }

        cache.set("complex-project", complex_data)
        result = cache.get("complex-project")
        assert result == complex_data


@pytest.mark.unit
class TestCacheClearAll:
    def test_clear_all_removes_all_cache_files(self, temp_cache_dir, monkeypatch):
        """Test that clear_all removes all cache files."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache.set("project-1", {"data": 1})
        cache.set("project-2", {"data": 2})
        cache.set("project-3", {"data": 3})

        cache_files_before = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files_before) == 3

        cache.clear_all()

        cache_files_after = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files_after) == 0

    def test_clear_all_handles_nonexistent_dir(self, temp_directory, monkeypatch):
        """Test that clear_all handles nonexistent cache directory."""
        cache_dir = temp_directory / "nonexistent"
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: cache_dir)
        cache = SimpleCache()
        cache.cache_dir = cache_dir

        cache.clear_all()

    def test_clear_all_handles_os_error(self, temp_cache_dir, monkeypatch):
        """Test that clear_all handles OS errors gracefully."""
        from unittest.mock import patch

        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache.set("test-project", {"data": 1})

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            cache.clear_all()

    def test_clear_all_preserves_non_json_files(self, temp_cache_dir, monkeypatch):
        """Test that clear_all only removes .json files."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache.set("project-1", {"data": 1})
        non_json_file = cache.cache_dir / "readme.txt"
        non_json_file.write_text("This is not a cache file")

        cache.clear_all()

        assert not list(cache.cache_dir.glob("*.json"))
        assert non_json_file.exists()


@pytest.mark.unit
class TestCacheIntegration:
    def test_full_cache_lifecycle(self, temp_cache_dir, monkeypatch):
        """Test complete cache lifecycle: set, get, expire, clear."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache(ttl_seconds=2)

        data = {"flags": [{"key": "test"}]}
        cache.set("lifecycle-test", data)

        result = cache.get("lifecycle-test")
        assert result == data

        time.sleep(2.1)
        expired_result = cache.get("lifecycle-test")
        assert expired_result is None

        cache.set("lifecycle-test", data)
        cache.clear_all()
        cleared_result = cache.get("lifecycle-test")
        assert cleared_result is None

    def test_multiple_projects_in_cache(self, temp_cache_dir, monkeypatch):
        """Test caching multiple projects simultaneously."""
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)
        cache = SimpleCache()

        cache.set("project-a", {"name": "A"})
        cache.set("project-b", {"name": "B"})
        cache.set("project-c", {"name": "C"})

        assert cache.get("project-a") == {"name": "A"}
        assert cache.get("project-b") == {"name": "B"}
        assert cache.get("project-c") == {"name": "C"}
