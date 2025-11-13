import json
import os
import time
from pathlib import Path
from platformdirs import user_cache_dir


class SimpleCache:
    """Simple file-based cache for API responses with TTL support."""

    def __init__(self, ttl_seconds=3600):
        """
        Initialize cache with TTL.

        Args:
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self.cache_dir = Path(user_cache_dir("launchdarkly-audit"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file(self, key):
        """Get cache file path for a given key."""
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key):
        """
        Retrieve data from cache if valid.

        Args:
            key: Cache key (e.g., project name)

        Returns:
            Cached data if valid, None otherwise
        """
        cache_file = self._get_cache_file(key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)

            timestamp = cached.get('timestamp', 0)
            current_time = time.time()

            if current_time - timestamp > self.ttl_seconds:
                return None

            return cached.get('data')
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, key, data):
        """
        Store data in cache with current timestamp.

        Args:
            key: Cache key (e.g., project name)
            data: Data to cache
        """
        cache_file = self._get_cache_file(key)

        try:
            cached = {
                'timestamp': time.time(),
                'data': data
            }

            with open(cache_file, 'w') as f:
                json.dump(cached, f)
        except OSError:
            pass

    def clear_all(self):
        """Remove all cache files."""
        if not self.cache_dir.exists():
            return

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except OSError:
                pass
