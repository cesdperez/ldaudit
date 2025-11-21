"""Shared test fixtures for the test suite."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def sample_flag_data():
    """Factory fixture for creating test flag data with various configurations."""

    def _make_flag(
        key="test-flag",
        name="Test Flag",
        kind="boolean",
        temporary=True,
        archived=False,
        environments=None,
        maintainer_first_name="John",
        maintainer_last_name="Doe",
        creation_date=None,
    ):
        if environments is None:
            environments = {
                "production": {
                    "on": True,
                    "lastModified": int((datetime.now() - timedelta(days=90)).timestamp() * 1000),
                },
                "staging": {
                    "on": False,
                    "lastModified": int((datetime.now() - timedelta(days=60)).timestamp() * 1000),
                },
            }

        if creation_date is None:
            creation_date = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)

        return {
            "key": key,
            "name": name,
            "kind": kind,
            "temporary": temporary,
            "archived": archived,
            "creationDate": creation_date,
            "environments": environments,
            "_maintainer": {
                "firstName": maintainer_first_name,
                "lastName": maintainer_last_name,
            },
        }

    return _make_flag


@pytest.fixture
def temporary_flag(sample_flag_data):
    """Fixture for a standard temporary flag."""
    return sample_flag_data(key="temp-flag", temporary=True, archived=False)


@pytest.fixture
def permanent_flag(sample_flag_data):
    """Fixture for a permanent flag."""
    return sample_flag_data(key="perm-flag", temporary=False, archived=False)


@pytest.fixture
def archived_flag(sample_flag_data):
    """Fixture for an archived flag."""
    return sample_flag_data(key="archived-flag", temporary=True, archived=True)


@pytest.fixture
def inactive_flag(sample_flag_data):
    """Fixture for an inactive flag (not modified in any environment for 6 months)."""
    six_months_ago = int((datetime.now() - timedelta(days=180)).timestamp() * 1000)
    return sample_flag_data(
        key="inactive-flag",
        temporary=True,
        archived=False,
        environments={
            "production": {"on": True, "lastModified": six_months_ago},
            "staging": {"on": False, "lastModified": six_months_ago},
        },
    )


@pytest.fixture
def active_flag(sample_flag_data):
    """Fixture for an active flag (recently modified)."""
    one_week_ago = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    return sample_flag_data(
        key="active-flag",
        temporary=True,
        archived=False,
        environments={
            "production": {"on": True, "lastModified": one_week_ago},
            "staging": {"on": False, "lastModified": one_week_ago},
        },
    )


@pytest.fixture
def mock_api_response(sample_flag_data):
    """Fixture for mock API responses."""

    def _make_response(items=None, total_count=None):
        if items is None:
            items = [
                sample_flag_data(key="flag-1", temporary=True),
                sample_flag_data(key="flag-2", temporary=False),
                sample_flag_data(key="flag-3", temporary=True, archived=True),
            ]

        return {"items": items, "totalCount": total_count if total_count is not None else len(items)}

    return _make_response


@pytest.fixture
def temp_directory():
    """Fixture that provides a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_cache_dir(temp_directory):
    """Fixture that provides a temporary cache directory."""
    cache_dir = temp_directory / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def sample_file_content():
    """Fixture providing sample file content for search tests."""
    return {
        "with_flag": """
def check_feature():
    if ld_client.variation('test-flag', user, False):
        print('Feature enabled')
""",
        "with_multiple_flags": """
def check_features():
    flag1 = ld_client.variation('flag-one', user, False)
    flag2 = ld_client.variation('flag-two', user, False)
    return flag1 and flag2
""",
        "without_flag": """
def normal_code():
    return True
""",
    }


@pytest.fixture
def mock_timestamps():
    """Fixture providing various timestamps for testing."""
    now = datetime.now()
    return {
        "now": int(now.timestamp() * 1000),
        "one_day_ago": int((now - timedelta(days=1)).timestamp() * 1000),
        "one_week_ago": int((now - timedelta(days=7)).timestamp() * 1000),
        "one_month_ago": int((now - timedelta(days=30)).timestamp() * 1000),
        "three_months_ago": int((now - timedelta(days=90)).timestamp() * 1000),
        "six_months_ago": int((now - timedelta(days=180)).timestamp() * 1000),
        "one_year_ago": int((now - timedelta(days=365)).timestamp() * 1000),
    }
