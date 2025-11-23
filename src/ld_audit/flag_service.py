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
