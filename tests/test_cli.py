import datetime

import pytest

from ld_audit.cli import parse_comma_separated
from ld_audit.config import DEFAULT_BASE_URL
from ld_audit.flag_service import FlagService
from ld_audit.formatters import create_flags_table, format_date, format_env_status, get_status_icon
from ld_audit.models import Flag


@pytest.mark.unit
class TestFlagService:
    def test_filter_by_inactivity_basic(self):
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flag_dict = {
            "key": "flag-1",
            "archived": False,
            "temporary": True,
            "creationDate": int(six_months_ago.timestamp() * 1000),
            "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            "_maintainer": {"firstName": "John"},
        }

        flags = [Flag.from_dict(flag_dict)]
        result = FlagService.filter_by_inactivity(flags, four_months_ago)

        assert len(result) == 1
        assert result[0].key == "flag-1"

    def test_filter_by_inactivity_modified_recently(self):
        now = datetime.datetime.now()
        three_months_ago = now - datetime.timedelta(days=90)
        one_month_ago = now - datetime.timedelta(days=30)

        flag_dict = {
            "key": "recent-flag",
            "archived": False,
            "temporary": True,
            "creationDate": int(three_months_ago.timestamp() * 1000),
            "environments": {"production": {"on": False, "lastModified": int(one_month_ago.timestamp() * 1000)}},
            "_maintainer": {"firstName": "John"},
        }

        flags = [Flag.from_dict(flag_dict)]
        result = FlagService.filter_by_inactivity(flags, three_months_ago)

        assert len(result) == 0

    def test_filter_by_inactivity_multiple_environments(self):
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        one_month_ago = now - datetime.timedelta(days=30)
        four_months_ago = now - datetime.timedelta(days=120)

        flag_dict = {
            "key": "multi-env-flag",
            "archived": False,
            "temporary": True,
            "creationDate": int(six_months_ago.timestamp() * 1000),
            "environments": {
                "production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)},
                "staging": {"on": False, "lastModified": int(one_month_ago.timestamp() * 1000)},
            },
            "_maintainer": {"firstName": "John"},
        }

        flags = [Flag.from_dict(flag_dict)]
        result = FlagService.filter_by_inactivity(flags, four_months_ago)

        assert len(result) == 0

    def test_filter_by_maintainer(self):
        flag_dict_john = {
            "key": "john-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {"production": {"on": False, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "John"},
        }
        flag_dict_jane = {
            "key": "jane-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {"production": {"on": False, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "Jane"},
        }

        flags = [Flag.from_dict(flag_dict_john), Flag.from_dict(flag_dict_jane)]
        result = FlagService.filter_by_maintainer(flags, ["John"])

        assert len(result) == 1
        assert result[0].key == "john-flag"

    def test_filter_by_archived(self):
        archived_dict = {
            "key": "archived-flag",
            "archived": True,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {"production": {"on": False, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "John"},
        }
        active_dict = {
            "key": "active-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {"production": {"on": False, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "John"},
        }

        flags = [Flag.from_dict(archived_dict), Flag.from_dict(active_dict)]
        result = FlagService.filter_by_archived(flags, archived=False)

        assert len(result) == 1
        assert result[0].key == "active-flag"

    def test_filter_by_temporary(self):
        temp_dict = {
            "key": "temp-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {"production": {"on": False, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "John"},
        }
        perm_dict = {
            "key": "perm-flag",
            "archived": False,
            "temporary": False,
            "creationDate": 1000000000,
            "environments": {"production": {"on": False, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "John"},
        }

        flags = [Flag.from_dict(temp_dict), Flag.from_dict(perm_dict)]
        result = FlagService.filter_by_temporary(flags, temporary=True)

        assert len(result) == 1
        assert result[0].key == "temp-flag"

    def test_filter_by_exclude_list(self):
        flag1_dict = {
            "key": "flag-1",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {"production": {"on": False, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "John"},
        }
        flag2_dict = {
            "key": "flag-2",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {"production": {"on": False, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "John"},
        }

        flags = [Flag.from_dict(flag1_dict), Flag.from_dict(flag2_dict)]
        result = FlagService.filter_by_exclude_list(flags, ["flag-2"])

        assert len(result) == 1
        assert result[0].key == "flag-1"

    def test_get_inactive_flags(self):
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        one_month_ago = now - datetime.timedelta(days=30)

        inactive_dict = {
            "key": "inactive-flag",
            "archived": False,
            "temporary": True,
            "creationDate": int(six_months_ago.timestamp() * 1000),
            "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            "_maintainer": {"firstName": "John"},
        }
        active_dict = {
            "key": "active-flag",
            "archived": False,
            "temporary": True,
            "creationDate": int(one_month_ago.timestamp() * 1000),
            "environments": {"production": {"on": False, "lastModified": int(one_month_ago.timestamp() * 1000)}},
            "_maintainer": {"firstName": "John"},
        }

        flags = [Flag.from_dict(inactive_dict), Flag.from_dict(active_dict)]
        result = FlagService.get_inactive_flags(flags, months=3)

        assert len(result) == 1
        assert result[0].key == "inactive-flag"


@pytest.mark.unit
class TestFormatEnvStatus:
    def test_format_env_status_multiple_envs_with_parens(self):
        flag_dict = {
            "key": "test-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {
                "production": {"on": False, "lastModified": 1000000000},
                "staging": {"on": True, "lastModified": 1000000000},
                "dev": {"on": True, "lastModified": 1000000000},
            },
            "_maintainer": {"firstName": "John"},
        }
        flag = Flag.from_dict(flag_dict)

        result = format_env_status(flag)
        assert "dev: ON" in result
        assert "production: OFF" in result
        assert "staging: ON" in result
        assert result.startswith("(")
        assert result.endswith(")")

    def test_format_env_status_multiple_envs_without_parens(self):
        flag_dict = {
            "key": "test-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {
                "production": {"on": False, "lastModified": 1000000000},
                "staging": {"on": True, "lastModified": 1000000000},
                "dev": {"on": True, "lastModified": 1000000000},
            },
            "_maintainer": {"firstName": "John"},
        }
        flag = Flag.from_dict(flag_dict)

        result = format_env_status(flag, include_parentheses=False)
        assert "dev: ON" in result
        assert "production: OFF" in result
        assert "staging: ON" in result
        assert not result.startswith("(")
        assert not result.endswith(")")

    def test_format_env_status_single_env(self):
        flag_dict = {
            "key": "test-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {"production": {"on": True, "lastModified": 1000000000}},
            "_maintainer": {"firstName": "John"},
        }
        flag = Flag.from_dict(flag_dict)

        result = format_env_status(flag)
        assert "production: ON" in result

    def test_format_env_status_no_environments_with_parens(self):
        flag_dict = {
            "key": "test-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {},
            "_maintainer": {"firstName": "John"},
        }
        flag = Flag.from_dict(flag_dict)

        result = format_env_status(flag)
        assert result == "(no environments)"

    def test_format_env_status_no_environments_without_parens(self):
        flag_dict = {
            "key": "test-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1000000000,
            "environments": {},
            "_maintainer": {"firstName": "John"},
        }
        flag = Flag.from_dict(flag_dict)

        result = format_env_status(flag, include_parentheses=False)
        assert result == "no environments"


@pytest.mark.unit
class TestFormatDate:
    @pytest.mark.parametrize(
        "timestamp,expected",
        [
            (1704067200000, "2024-01-01"),
            (0, "1970-01-01"),
            (1609459200000, "2021-01-01"),
        ],
    )
    def test_format_date(self, timestamp, expected):
        result = format_date(timestamp)
        assert result == expected


@pytest.mark.unit
class TestParseCommaSeparated:
    @pytest.mark.parametrize(
        "input_value,expected",
        [
            (["cs,js,ts"], ["cs", "js", "ts"]),
            (["cs", "js", "ts"], ["cs", "js", "ts"]),
            (["cs,js", "ts"], ["cs", "js", "ts"]),
            (["cs, js , ts"], ["cs", "js", "ts"]),
            (None, None),
            ([], None),
            (["", ","], None),
        ],
    )
    def test_parse_comma_separated(self, input_value, expected):
        result = parse_comma_separated(input_value)
        assert result == expected


@pytest.mark.unit
class TestGetStatusIcon:
    def test_get_status_icon_on(self):
        """Test status icon for ON state."""
        result = get_status_icon(True)
        assert "ON" in result.plain
        assert result.style == "green bold"

    def test_get_status_icon_off(self):
        """Test status icon for OFF state."""
        result = get_status_icon(False)
        assert "OFF" in result.plain
        assert result.style == "red bold"


@pytest.mark.unit
class TestCreateFlagsTable:
    def test_create_flags_table_basic(self):
        """Test creating a basic flags table."""
        flag_dict = {
            "key": "test-flag",
            "archived": False,
            "temporary": True,
            "creationDate": 1704067200000,
            "environments": {"production": {"on": True, "lastModified": 1704067200000}},
            "_maintainer": {"firstName": "John"},
        }
        flags = [Flag.from_dict(flag_dict)]

        table = create_flags_table(flags, "test-project", DEFAULT_BASE_URL)

        assert table is not None
        assert len(table.columns) == 5

    def test_create_flags_table_multiple_flags(self):
        """Test creating a table with multiple flags."""
        flags = [
            Flag.from_dict(
                {
                    "key": f"flag-{i}",
                    "archived": False,
                    "temporary": True,
                    "creationDate": 1704067200000,
                    "environments": {"production": {"on": True, "lastModified": 1704067200000}},
                    "_maintainer": {"firstName": "John"},
                }
            )
            for i in range(3)
        ]

        table = create_flags_table(flags, "test-project", DEFAULT_BASE_URL)

        assert table is not None
        assert len(table.rows) == 3

    def test_create_flags_table_empty(self):
        """Test creating a table with no flags."""
        table = create_flags_table([], "test-project", DEFAULT_BASE_URL)

        assert table is not None
        assert len(table.rows) == 0
