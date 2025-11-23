import datetime

import pytest

from ld_audit.cli import (
    DEFAULT_BASE_URL,
    create_flags_table,
    filter_flags,
    format_date,
    format_env_status,
    get_env_value,
    get_inactive_flags,
    get_status_icon,
    parse_comma_separated,
)


@pytest.mark.unit
class TestGetEnvValue:
    def test_get_env_value_with_default_env(self):
        flag = {"environments": {"production": {"on": True, "lastModified": 1234567890000}}}
        assert get_env_value(flag, "production") is True
        assert get_env_value(flag, "production", key="lastModified") == 1234567890000

    def test_get_env_value_with_custom_env(self):
        flag = {"environments": {"staging": {"on": False}}}
        assert get_env_value(flag, env="staging") is False

    def test_get_env_value_missing_env(self):
        flag = {"environments": {"dev": {"on": True}}}
        assert get_env_value(flag, env="production", default=None) is None

    def test_get_env_value_missing_key(self):
        flag = {"environments": {"production": {"on": True}}}
        assert get_env_value(flag, "production", key="missing", default="fallback") == "fallback"

    def test_get_env_value_no_environments(self):
        flag = {}
        assert get_env_value(flag, "production", default=False) is False


@pytest.mark.unit
class TestFilterFlags:
    def test_filter_flags_basic(self):
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "flag-1",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            }
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
        )

        assert len(result) == 1
        assert result[0]["key"] == "flag-1"

    def test_filter_flags_modified_recently(self):
        now = datetime.datetime.now()
        three_months_ago = now - datetime.timedelta(days=90)
        one_month_ago = now - datetime.timedelta(days=30)

        flags = [
            {
                "key": "recent-flag",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(one_month_ago.timestamp() * 1000)}},
            }
        ]

        result = filter_flags(
            items=flags,
            modified_before=three_months_ago,
            is_archived=False,
            is_temporary=True,
        )

        assert len(result) == 0

    def test_filter_flags_multiple_environments(self):
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        one_month_ago = now - datetime.timedelta(days=30)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "multi-env-flag",
                "archived": False,
                "temporary": True,
                "environments": {
                    "production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)},
                    "staging": {"on": False, "lastModified": int(one_month_ago.timestamp() * 1000)},
                },
            }
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
        )

        assert len(result) == 0

    def test_filter_flags_by_maintainer(self):
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "john-flag",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
                "_maintainer": {"firstName": "John"},
            },
            {
                "key": "jane-flag",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
                "_maintainer": {"firstName": "Jane"},
            },
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
            maintainers=["John"],
        )

        assert len(result) == 1
        assert result[0]["key"] == "john-flag"

    def test_filter_flags_archived(self):
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "archived-flag",
                "archived": True,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            }
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
        )

        assert len(result) == 0

    def test_filter_flags_permanent(self):
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "permanent-flag",
                "archived": False,
                "temporary": False,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            }
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
        )

        assert len(result) == 0

    def test_filter_flags_includes_on_flags(self):
        """Test that ON flags are now included (ON/OFF filtering removed)"""
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "on-flag",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": True, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            }
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
        )

        # Should include flag regardless of ON/OFF state
        assert len(result) == 1

    def test_filter_flags_with_any_environment(self):
        """Test that flags work regardless of which environments they have"""
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "staging-only-flag",
                "archived": False,
                "temporary": True,
                "environments": {"staging": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            }
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
        )

        # Should include flag regardless of which environment it's in
        assert len(result) == 1

    def test_filter_flags_with_exclude_list(self):
        """Test that exclude_list parameter filters out specified flags"""
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "flag-1",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            },
            {
                "key": "flag-2",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            },
            {
                "key": "flag-3",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            },
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
            exclude_list=["flag-2"],
        )

        assert len(result) == 2
        assert result[0]["key"] == "flag-1"
        assert result[1]["key"] == "flag-3"

    def test_filter_flags_with_multiple_excludes(self):
        """Test that multiple flags can be excluded"""
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "keep-flag",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            },
            {
                "key": "exclude-1",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            },
            {
                "key": "exclude-2",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
            },
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
            exclude_list=["exclude-1", "exclude-2"],
        )

        assert len(result) == 1
        assert result[0]["key"] == "keep-flag"

    def test_filter_flags_exclude_list_with_maintainer(self):
        """Test that exclude_list and maintainer filters work together"""
        now = datetime.datetime.now()
        six_months_ago = now - datetime.timedelta(days=180)
        four_months_ago = now - datetime.timedelta(days=120)

        flags = [
            {
                "key": "john-flag-1",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
                "_maintainer": {"firstName": "John"},
            },
            {
                "key": "john-flag-2",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
                "_maintainer": {"firstName": "John"},
            },
            {
                "key": "jane-flag",
                "archived": False,
                "temporary": True,
                "environments": {"production": {"on": False, "lastModified": int(six_months_ago.timestamp() * 1000)}},
                "_maintainer": {"firstName": "Jane"},
            },
        ]

        result = filter_flags(
            items=flags,
            modified_before=four_months_ago,
            is_archived=False,
            is_temporary=True,
            maintainers=["John"],
            exclude_list=["john-flag-2"],
        )

        assert len(result) == 1
        assert result[0]["key"] == "john-flag-1"


@pytest.mark.unit
class TestFormatEnvStatus:
    def test_format_env_status_multiple_envs_with_parens(self):
        flag = {
            "environments": {
                "production": {"on": False},
                "staging": {"on": True},
                "dev": {"on": True},
            }
        }
        result = format_env_status(flag)
        assert "dev: ON" in result
        assert "production: OFF" in result
        assert "staging: ON" in result
        assert result.startswith("(")
        assert result.endswith(")")

    def test_format_env_status_multiple_envs_without_parens(self):
        flag = {
            "environments": {
                "production": {"on": False},
                "staging": {"on": True},
                "dev": {"on": True},
            }
        }
        result = format_env_status(flag, include_parentheses=False)
        assert "dev: ON" in result
        assert "production: OFF" in result
        assert "staging: ON" in result
        assert not result.startswith("(")
        assert not result.endswith(")")

    def test_format_env_status_single_env(self):
        flag = {"environments": {"production": {"on": True}}}
        result = format_env_status(flag)
        assert "production: ON" in result

    def test_format_env_status_no_environments_with_parens(self):
        flag = {}
        result = format_env_status(flag)
        assert result == "(no environments)"

    def test_format_env_status_no_environments_without_parens(self):
        flag = {}
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
    def test_create_flags_table_basic(self, sample_flag_data):
        """Test creating a basic flags table."""
        flags = [sample_flag_data(key="test-flag")]

        table = create_flags_table(flags, "test-project", DEFAULT_BASE_URL)

        assert table is not None
        assert len(table.columns) == 5

    def test_create_flags_table_multiple_flags(self, sample_flag_data):
        """Test creating a table with multiple flags."""
        flags = [
            sample_flag_data(key="flag-1"),
            sample_flag_data(key="flag-2"),
            sample_flag_data(key="flag-3"),
        ]

        table = create_flags_table(flags, "test-project", DEFAULT_BASE_URL)

        assert table is not None
        assert len(table.rows) == 3

    def test_create_flags_table_empty(self):
        """Test creating a table with no flags."""
        table = create_flags_table([], "test-project", DEFAULT_BASE_URL)

        assert table is not None
        assert len(table.rows) == 0

    def test_create_flags_table_with_no_maintainer(self, sample_flag_data):
        """Test creating a table with flag missing maintainer."""
        flag = sample_flag_data(key="test-flag")
        del flag["_maintainer"]

        table = create_flags_table([flag], "test-project", DEFAULT_BASE_URL)

        assert table is not None
        assert len(table.rows) == 1


@pytest.mark.integration
class TestGetInactiveFlags:
    def test_get_inactive_flags_integration(self, inactive_flag, active_flag, temp_cache_dir, monkeypatch):
        """Test get_inactive_flags integration with fetch and filter."""
        from unittest.mock import patch

        from ld_audit.cache import SimpleCache

        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        with patch("ld_audit.cli.fetch_all_live_flags") as mock_fetch:
            mock_fetch.return_value = {
                "items": [inactive_flag, active_flag],
                "totalCount": 2,
            }

            result = get_inactive_flags(
                project="test-project",
                months=3,
                base_url=DEFAULT_BASE_URL,
                cache=cache,
            )

            assert len(result) == 1
            assert result[0]["key"] == "inactive-flag"

    def test_get_inactive_flags_with_maintainer_filter(
        self, inactive_flag, temp_cache_dir, monkeypatch, sample_flag_data
    ):
        """Test get_inactive_flags with maintainer filter."""
        from unittest.mock import patch

        from ld_audit.cache import SimpleCache

        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        six_months_ago = int((datetime.datetime.now() - datetime.timedelta(days=180)).timestamp() * 1000)
        john_flag = sample_flag_data(
            key="john-inactive",
            temporary=True,
            archived=False,
            maintainer_first_name="John",
            environments={"production": {"on": True, "lastModified": six_months_ago}},
        )
        jane_flag = sample_flag_data(
            key="jane-inactive",
            temporary=True,
            archived=False,
            maintainer_first_name="Jane",
            environments={"production": {"on": True, "lastModified": six_months_ago}},
        )

        with patch("ld_audit.cli.fetch_all_live_flags") as mock_fetch:
            mock_fetch.return_value = {
                "items": [john_flag, jane_flag],
                "totalCount": 2,
            }

            result = get_inactive_flags(
                project="test-project",
                months=3,
                base_url=DEFAULT_BASE_URL,
                cache=cache,
                maintainers=["John"],
            )

            assert len(result) == 1
            assert result[0]["key"] == "john-inactive"

    def test_get_inactive_flags_with_exclude_list(self, inactive_flag, temp_cache_dir, monkeypatch, sample_flag_data):
        """Test get_inactive_flags with exclude list."""
        from unittest.mock import patch

        from ld_audit.cache import SimpleCache

        monkeypatch.setenv("LD_API_KEY", "test-api-key")
        monkeypatch.setattr("ld_audit.cache.user_cache_dir", lambda _: temp_cache_dir)

        import ld_audit.cli as cli_module

        monkeypatch.setattr(cli_module, "api_key", "test-api-key")

        cache = SimpleCache()

        six_months_ago = int((datetime.datetime.now() - datetime.timedelta(days=180)).timestamp() * 1000)
        flag1 = sample_flag_data(
            key="keep-flag",
            temporary=True,
            archived=False,
            environments={"production": {"on": True, "lastModified": six_months_ago}},
        )
        flag2 = sample_flag_data(
            key="exclude-flag",
            temporary=True,
            archived=False,
            environments={"production": {"on": True, "lastModified": six_months_ago}},
        )

        with patch("ld_audit.cli.fetch_all_live_flags") as mock_fetch:
            mock_fetch.return_value = {
                "items": [flag1, flag2],
                "totalCount": 2,
            }

            result = get_inactive_flags(
                project="test-project",
                months=3,
                base_url=DEFAULT_BASE_URL,
                cache=cache,
                exclude_list=["exclude-flag"],
            )

            assert len(result) == 1
            assert result[0]["key"] == "keep-flag"
