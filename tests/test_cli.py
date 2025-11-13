import datetime

from ld_audit.cli import (
    DEFAULT_ENV_ORDER,
    filter_flags,
    format_date,
    get_env_value,
    get_primary_env,
    parse_comma_separated,
)

# For backward compatibility in tests
DEFAULT_ENV_LIST = DEFAULT_ENV_ORDER.split(",")
DEFAULT_ENV = DEFAULT_ENV_LIST[0]


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


class TestGetPrimaryEnv:
    def test_get_primary_env_with_production(self):
        flag = {"environments": {"production": {}, "staging": {}, "dev": {}}}
        assert get_primary_env(flag, DEFAULT_ENV_LIST) == "production"

    def test_get_primary_env_fallback_to_staging(self):
        flag = {"environments": {"staging": {}, "dev": {}, "test": {}}}
        assert get_primary_env(flag, DEFAULT_ENV_LIST) == "staging"

    def test_get_primary_env_fallback_to_dev(self):
        flag = {"environments": {"dev": {}, "test": {}}}
        assert get_primary_env(flag, DEFAULT_ENV_LIST) == "dev"

    def test_get_primary_env_custom_env_only(self):
        flag = {"environments": {"custom-env": {}, "another-env": {}}}
        result = get_primary_env(flag, DEFAULT_ENV_LIST)
        assert result in ["another-env", "custom-env"]

    def test_get_primary_env_no_environments(self):
        flag = {}
        assert get_primary_env(flag, DEFAULT_ENV_LIST) == DEFAULT_ENV

    def test_get_primary_env_empty_environments(self):
        flag = {"environments": {}}
        assert get_primary_env(flag, DEFAULT_ENV_LIST) == DEFAULT_ENV


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
            is_on=False,
            env_order=DEFAULT_ENV_LIST,
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
            is_on=False,
            env_order=DEFAULT_ENV_LIST,
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
            is_on=False,
            env_order=DEFAULT_ENV_LIST,
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
            is_on=False,
            env_order=DEFAULT_ENV_LIST,
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
            is_on=False,
            env_order=DEFAULT_ENV_LIST,
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
            is_on=False,
            env_order=DEFAULT_ENV_LIST,
        )

        assert len(result) == 0

    def test_filter_flags_on_status(self):
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
            is_on=False,
            env_order=DEFAULT_ENV_LIST,
        )

        assert len(result) == 0

    def test_filter_flags_no_production_fallback(self):
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
            is_on=False,
            env_order=DEFAULT_ENV_LIST,
        )

        assert len(result) == 1


class TestFormatDate:
    def test_format_date_valid(self):
        timestamp = 1704067200000
        result = format_date(timestamp)
        assert result == "2024-01-01"

    def test_format_date_zero(self):
        result = format_date(0)
        assert result == "1970-01-01"


class TestParseCommaSeparated:
    def test_parse_comma_separated_single(self):
        result = parse_comma_separated(["cs,js,ts"])
        assert result == ["cs", "js", "ts"]

    def test_parse_comma_separated_multiple(self):
        result = parse_comma_separated(["cs", "js", "ts"])
        assert result == ["cs", "js", "ts"]

    def test_parse_comma_separated_mixed(self):
        result = parse_comma_separated(["cs,js", "ts"])
        assert result == ["cs", "js", "ts"]

    def test_parse_comma_separated_with_spaces(self):
        result = parse_comma_separated(["cs, js , ts"])
        assert result == ["cs", "js", "ts"]

    def test_parse_comma_separated_none(self):
        result = parse_comma_separated(None)
        assert result is None

    def test_parse_comma_separated_empty_list(self):
        result = parse_comma_separated([])
        assert result is None

    def test_parse_comma_separated_empty_strings(self):
        result = parse_comma_separated(["", ","])
        assert result is None
