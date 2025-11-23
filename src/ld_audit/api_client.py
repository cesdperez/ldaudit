"""LaunchDarkly API client for fetching feature flags."""

import requests

from ld_audit.cache import SimpleCache
from ld_audit.models import Flag


class LaunchDarklyAPIError(Exception):
    """Exception raised for LaunchDarkly API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class LaunchDarklyClient:
    """Client for interacting with LaunchDarkly REST API."""

    def __init__(self, api_key: str, base_url: str, cache: SimpleCache):
        """
        Initialize LaunchDarkly API client.

        Args:
            api_key: LaunchDarkly API key
            base_url: Base URL for LaunchDarkly API
            cache: Cache instance for storing responses
        """
        self.api_key = api_key
        self.base_url = base_url
        self.cache = cache

    def get_all_flags(self, project: str, enable_cache: bool = True, force_refresh: bool = False) -> list[Flag]:
        """
        Fetch all flags from LaunchDarkly API for a given project.

        Args:
            project: LaunchDarkly project name
            enable_cache: Whether to use cached data if available
            force_refresh: Force refresh from API and update cache

        Returns:
            List of Flag objects

        Raises:
            LaunchDarklyAPIError: If API request fails
        """
        if enable_cache and not force_refresh:
            cached_data = self.cache.get(project)
            if cached_data is not None:
                return self._parse_flags_response(cached_data)

        url = f"{self.base_url}/api/v2/flags/{project}"
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if enable_cache or force_refresh:
                self.cache.set(project, data)

            return self._parse_flags_response(data)

        except requests.exceptions.HTTPError:
            if response.status_code == 401:
                raise LaunchDarklyAPIError("Invalid or expired API key. Check your LD_API_KEY.", status_code=401)
            elif response.status_code == 404:
                raise LaunchDarklyAPIError(f"Project '{project}' not found", status_code=404)
            else:
                raise LaunchDarklyAPIError(
                    f"HTTP error occurred: {response.status_code}", status_code=response.status_code
                )

        except requests.exceptions.RequestException as e:
            raise LaunchDarklyAPIError(f"Network error: {e}")

    def _parse_flags_response(self, data: dict) -> list[Flag]:
        """Parse API response into Flag objects."""
        items = data.get("items", [])
        return [Flag.from_dict(item) for item in items]
