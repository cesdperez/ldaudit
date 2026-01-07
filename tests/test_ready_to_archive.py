"""Tests for ready-to-archive functionality."""

from datetime import datetime, timedelta

from ld_audit.flag_service import FlagService
from ld_audit.models import Flag


class TestFlagIsReadyToArchive:
    """Tests for Flag.is_ready_to_archive() method."""

    def test_ready_to_archive_all_criteria_met(self, dict_to_flag, sample_flag_data):
        """Test flag meeting all ready-to-archive criteria returns True."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="ready-flag",
            temporary=True,
            archived=False,
            creation_date=old_creation,
            code_references_count=0,
        )
        flag = dict_to_flag(flag_data)
        # last_requested is None by default (not recently requested)

        assert flag.is_ready_to_archive() is True

    def test_not_ready_permanent_flag(self, dict_to_flag, sample_flag_data):
        """Test permanent flag is not ready to archive."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="permanent-flag",
            temporary=False,  # Permanent
            archived=False,
            creation_date=old_creation,
            code_references_count=0,
        )
        flag = dict_to_flag(flag_data)

        assert flag.is_ready_to_archive() is False

    def test_not_ready_archived_flag(self, dict_to_flag, sample_flag_data):
        """Test already archived flag is not ready to archive."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="archived-flag",
            temporary=True,
            archived=True,  # Already archived
            creation_date=old_creation,
            code_references_count=0,
        )
        flag = dict_to_flag(flag_data)

        assert flag.is_ready_to_archive() is False

    def test_not_ready_too_young(self, dict_to_flag, sample_flag_data):
        """Test flag younger than min_age_days is not ready to archive."""
        young_creation = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="young-flag",
            temporary=True,
            archived=False,
            creation_date=young_creation,  # Only 10 days old
            code_references_count=0,
        )
        flag = dict_to_flag(flag_data)

        assert flag.is_ready_to_archive() is False

    def test_not_ready_has_code_references(self, dict_to_flag, sample_flag_data):
        """Test flag with code references is not ready to archive."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="has-refs-flag",
            temporary=True,
            archived=False,
            creation_date=old_creation,
            code_references_count=5,  # Has code refs
        )
        flag = dict_to_flag(flag_data)

        assert flag.is_ready_to_archive() is False

    def test_not_ready_recently_requested(self, dict_to_flag, sample_flag_data):
        """Test flag recently requested is not ready to archive."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="recently-requested-flag",
            temporary=True,
            archived=False,
            creation_date=old_creation,
            code_references_count=0,
        )
        flag = dict_to_flag(flag_data)
        # Set last_requested to 3 days ago (within 7-day window)
        flag.last_requested = datetime.now() - timedelta(days=3)

        assert flag.is_ready_to_archive() is False

    def test_ready_with_old_request(self, dict_to_flag, sample_flag_data):
        """Test flag with old request is ready to archive."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="old-request-flag",
            temporary=True,
            archived=False,
            creation_date=old_creation,
            code_references_count=0,
        )
        flag = dict_to_flag(flag_data)
        # Set last_requested to 30 days ago (outside 7-day window)
        flag.last_requested = datetime.now() - timedelta(days=30)

        assert flag.is_ready_to_archive() is True

    def test_custom_min_age_days(self, dict_to_flag, sample_flag_data):
        """Test custom min_age_days parameter."""
        # Flag is 45 days old
        creation = int((datetime.now() - timedelta(days=45)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="custom-age-flag",
            temporary=True,
            archived=False,
            creation_date=creation,
            code_references_count=0,
        )
        flag = dict_to_flag(flag_data)

        # Default 30 days - should be ready
        assert flag.is_ready_to_archive(min_age_days=30) is True
        # Custom 60 days - should not be ready
        assert flag.is_ready_to_archive(min_age_days=60) is False

    def test_custom_eval_window_days(self, dict_to_flag, sample_flag_data):
        """Test custom eval_window_days parameter."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
        flag_data = sample_flag_data(
            key="custom-eval-flag",
            temporary=True,
            archived=False,
            creation_date=old_creation,
            code_references_count=0,
        )
        flag = dict_to_flag(flag_data)
        # Set last_requested to 5 days ago
        flag.last_requested = datetime.now() - timedelta(days=5)

        # Default 7 days - not ready (requested 5 days ago)
        assert flag.is_ready_to_archive(eval_window_days=7) is False
        # Custom 3 days - ready (requested 5 days ago > 3 day window)
        assert flag.is_ready_to_archive(eval_window_days=3) is True


class TestFlagServiceGetReadyToArchive:
    """Tests for FlagService.get_ready_to_archive_flags() method."""

    def test_filters_ready_flags(self, dicts_to_flags, sample_flag_data):
        """Test that only ready-to-archive flags are returned."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)
        young_creation = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)

        flags_data = [
            # Ready to archive
            sample_flag_data(key="ready-1", temporary=True, archived=False, creation_date=old_creation),
            # Not ready - permanent
            sample_flag_data(key="permanent", temporary=False, archived=False, creation_date=old_creation),
            # Not ready - too young
            sample_flag_data(key="young", temporary=True, archived=False, creation_date=young_creation),
            # Not ready - has code refs
            sample_flag_data(
                key="has-refs",
                temporary=True,
                archived=False,
                creation_date=old_creation,
                code_references_count=3,
            ),
        ]
        flags = dicts_to_flags(flags_data)

        result = FlagService.get_ready_to_archive_flags(flags)

        assert len(result) == 1
        assert result[0].key == "ready-1"

    def test_applies_maintainer_filter(self, dicts_to_flags, sample_flag_data):
        """Test that maintainer filter is applied."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)

        flags_data = [
            sample_flag_data(
                key="john-flag",
                temporary=True,
                archived=False,
                creation_date=old_creation,
                maintainer_first_name="John",
            ),
            sample_flag_data(
                key="jane-flag",
                temporary=True,
                archived=False,
                creation_date=old_creation,
                maintainer_first_name="Jane",
            ),
        ]
        flags = dicts_to_flags(flags_data)

        result = FlagService.get_ready_to_archive_flags(flags, maintainers=["John"])

        assert len(result) == 1
        assert result[0].key == "john-flag"

    def test_applies_exclude_filter(self, dicts_to_flags, sample_flag_data):
        """Test that exclude filter is applied."""
        old_creation = int((datetime.now() - timedelta(days=60)).timestamp() * 1000)

        flags_data = [
            sample_flag_data(key="keep-flag", temporary=True, archived=False, creation_date=old_creation),
            sample_flag_data(key="exclude-flag", temporary=True, archived=False, creation_date=old_creation),
        ]
        flags = dicts_to_flags(flags_data)

        result = FlagService.get_ready_to_archive_flags(flags, exclude_list=["exclude-flag"])

        assert len(result) == 1
        assert result[0].key == "keep-flag"

    def test_empty_when_no_flags_ready(self, dicts_to_flags, sample_flag_data):
        """Test empty result when no flags are ready to archive."""
        young_creation = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)

        flags_data = [
            sample_flag_data(key="young-1", temporary=True, archived=False, creation_date=young_creation),
            sample_flag_data(key="young-2", temporary=True, archived=False, creation_date=young_creation),
        ]
        flags = dicts_to_flags(flags_data)

        result = FlagService.get_ready_to_archive_flags(flags)

        assert len(result) == 0


class TestFlagServiceEnrichWithStatuses:
    """Tests for FlagService.enrich_flags_with_statuses() method."""

    def test_enriches_flags_with_last_requested(self, dict_to_flag, sample_flag_data):
        """Test that flags are enriched with lastRequested from statuses."""
        flag_data = sample_flag_data(key="test-flag")
        flag = dict_to_flag(flag_data)

        statuses = {
            "test-flag": {
                "name": "active",
                "lastRequested": "2025-01-01T12:00:00Z",
            }
        }

        FlagService.enrich_flags_with_statuses([flag], statuses)

        assert flag.last_requested is not None
        assert flag.last_requested.year == 2025
        assert flag.last_requested.month == 1
        assert flag.last_requested.day == 1

    def test_handles_missing_status(self, dict_to_flag, sample_flag_data):
        """Test that missing status results in None last_requested."""
        flag_data = sample_flag_data(key="test-flag")
        flag = dict_to_flag(flag_data)

        statuses = {}  # No status for this flag

        FlagService.enrich_flags_with_statuses([flag], statuses)

        assert flag.last_requested is None

    def test_handles_null_last_requested(self, dict_to_flag, sample_flag_data):
        """Test that null lastRequested results in None last_requested."""
        flag_data = sample_flag_data(key="test-flag")
        flag = dict_to_flag(flag_data)

        statuses = {
            "test-flag": {
                "name": "new",
                "lastRequested": None,
            }
        }

        FlagService.enrich_flags_with_statuses([flag], statuses)

        assert flag.last_requested is None


class TestFlagModelParsing:
    """Tests for Flag model parsing of expanded API response fields."""

    def test_parses_code_references_count(self):
        """Test that code references count is parsed from API response."""
        flag_data = {
            "key": "test-flag",
            "name": "Test Flag",
            "temporary": True,
            "archived": False,
            "creationDate": 1000,
            "environments": {},
            "_maintainer": {"firstName": "John"},
            "_codeReferences": {"total": 42},
        }

        flag = Flag.from_dict(flag_data)

        assert flag.code_references_count == 42

    def test_parses_code_references_count_defaults_to_zero(self):
        """Test that code references count defaults to 0 when not present."""
        flag_data = {
            "key": "test-flag",
            "name": "Test Flag",
            "temporary": True,
            "archived": False,
            "creationDate": 1000,
            "environments": {},
            "_maintainer": {"firstName": "John"},
        }

        flag = Flag.from_dict(flag_data)

        assert flag.code_references_count == 0

    def test_last_requested_defaults_to_none(self):
        """Test that last_requested defaults to None (set later by enrich)."""
        flag_data = {
            "key": "test-flag",
            "name": "Test Flag",
            "temporary": True,
            "archived": False,
            "creationDate": 1000,
            "environments": {},
            "_maintainer": {"firstName": "John"},
        }

        flag = Flag.from_dict(flag_data)

        assert flag.last_requested is None
