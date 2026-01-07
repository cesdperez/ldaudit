"""Business logic for filtering and analyzing feature flags."""

import datetime

from ld_audit.config import DAYS_PER_MONTH
from ld_audit.models import Flag


class FlagService:
    """Service for filtering and analyzing feature flags."""

    @staticmethod
    def filter_by_archived(flags: list[Flag], archived: bool) -> list[Flag]:
        """Filter flags by archived status."""
        return [flag for flag in flags if flag.archived == archived]

    @staticmethod
    def filter_by_temporary(flags: list[Flag], temporary: bool) -> list[Flag]:
        """Filter flags by temporary status."""
        return [flag for flag in flags if flag.temporary == temporary]

    @staticmethod
    def filter_by_inactivity(flags: list[Flag], threshold: datetime.datetime) -> list[Flag]:
        """Filter flags that haven't been modified in any environment since threshold."""
        return [flag for flag in flags if flag.is_inactive_since(threshold)]

    @staticmethod
    def filter_by_maintainer(flags: list[Flag], maintainer_names: list[str]) -> list[Flag]:
        """Filter flags by maintainer first name."""
        return [flag for flag in flags if flag.maintainer.first_name in maintainer_names]

    @staticmethod
    def filter_by_exclude_list(flags: list[Flag], exclude_keys: list[str]) -> list[Flag]:
        """Exclude flags with keys in the exclude list."""
        return [flag for flag in flags if flag.key not in exclude_keys]

    @staticmethod
    def get_inactive_flags(
        flags: list[Flag],
        months: int,
        maintainers: list[str] | None = None,
        exclude_list: list[str] | None = None,
    ) -> list[Flag]:
        """
        Get inactive temporary flags based on criteria.

        Args:
            flags: List of all flags
            months: Inactivity threshold in months
            maintainers: Optional list of maintainer names to filter by
            exclude_list: Optional list of flag keys to exclude

        Returns:
            List of inactive flags matching criteria
        """
        modified_before = datetime.datetime.now() - datetime.timedelta(days=months * DAYS_PER_MONTH)

        result = FlagService.filter_by_archived(flags, archived=False)
        result = FlagService.filter_by_temporary(result, temporary=True)
        result = FlagService.filter_by_inactivity(result, threshold=modified_before)

        if maintainers:
            result = FlagService.filter_by_maintainer(result, maintainers)

        if exclude_list:
            result = FlagService.filter_by_exclude_list(result, exclude_list)

        return result

    @staticmethod
    def apply_common_filters(
        flags: list[Flag], maintainers: list[str] | None = None, exclude_list: list[str] | None = None
    ) -> list[Flag]:
        """
        Apply common maintainer and exclude filters.

        Args:
            flags: List of flags
            maintainers: Optional list of maintainer names to filter by
            exclude_list: Optional list of flag keys to exclude

        Returns:
            Filtered list of flags
        """
        result = flags

        if maintainers:
            result = FlagService.filter_by_maintainer(result, maintainers)

        if exclude_list:
            result = FlagService.filter_by_exclude_list(result, exclude_list)

        return result

    @staticmethod
    def get_ready_to_archive_flags(
        flags: list[Flag],
        min_age_days: int = 30,
        eval_window_days: int = 7,
        maintainers: list[str] | None = None,
        exclude_list: list[str] | None = None,
    ) -> list[Flag]:
        """
        Get flags that are ready to archive based on LaunchDarkly criteria.

        A flag is ready to archive when:
        - It is temporary (not permanent)
        - It is not already archived
        - It is older than min_age_days
        - It has no code references
        - It has not been requested in the past eval_window_days

        Note: Flags must be enriched with status data first using enrich_flags_with_statuses().

        Args:
            flags: List of all flags (should be enriched with status data)
            min_age_days: Minimum flag age in days (default: 30)
            eval_window_days: Days without requests (default: 7)
            maintainers: Optional list of maintainer names to filter by
            exclude_list: Optional list of flag keys to exclude

        Returns:
            List of flags ready to archive
        """
        result = [flag for flag in flags if flag.is_ready_to_archive(min_age_days, eval_window_days)]

        if maintainers:
            result = FlagService.filter_by_maintainer(result, maintainers)

        if exclude_list:
            result = FlagService.filter_by_exclude_list(result, exclude_list)

        return result

    @staticmethod
    def enrich_flags_with_statuses(flags: list[Flag], statuses: dict[str, dict]) -> None:
        """
        Enrich flags with lastRequested data from flag-statuses API.

        This modifies the flags in place, setting the last_requested field.

        Args:
            flags: List of Flag objects to enrich
            statuses: Dictionary mapping flag key to status data from get_flag_statuses()
        """
        for flag in flags:
            status = statuses.get(flag.key, {})
            last_requested_str = status.get("lastRequested")
            if last_requested_str:
                try:
                    # Parse ISO format like "2016-08-16T21:10:11.886Z"
                    last_requested = datetime.datetime.fromisoformat(last_requested_str.replace("Z", "+00:00"))
                    # Convert to naive datetime for comparison
                    flag.last_requested = last_requested.replace(tzinfo=None)
                except (ValueError, AttributeError):
                    flag.last_requested = None
            else:
                flag.last_requested = None
