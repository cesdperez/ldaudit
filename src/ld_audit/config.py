"""Configuration constants and settings for ldaudit."""

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://app.launchdarkly.com"
DEFAULT_CACHE_TTL = 3600
DEFAULT_MAX_FILE_SIZE_MB = 5
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "dist",
    "build",
    "venv",
    "env",
    ".pytest_cache",
    "bin",
    "obj",
}

MILLISECONDS_TO_SECONDS = 1000.0
MB_TO_BYTES = 1024 * 1024
DAYS_PER_MONTH = 30


def get_api_key() -> str | None:
    """Get LaunchDarkly API key from environment."""
    return os.getenv("LD_API_KEY")
