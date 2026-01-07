"""Data models for LaunchDarkly feature flags."""

import datetime
from dataclasses import dataclass
from typing import Any


@dataclass
class Maintainer:
    """Represents a flag maintainer."""

    first_name: str
    last_name: str | None = None
    email: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Maintainer":
        """Create Maintainer from API response dictionary."""
        return cls(
            first_name=data.get("firstName", "Unknown"),
            last_name=data.get("lastName"),
            email=data.get("email"),
        )


@dataclass
class Environment:
    """Represents a flag environment configuration."""

    name: str
    is_on: bool
    last_modified: datetime.datetime

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "Environment":
        """Create Environment from API response dictionary."""
        last_modified_ms = data.get("lastModified", 0)
        last_modified = datetime.datetime.fromtimestamp(last_modified_ms / 1000.0)

        return cls(name=name, is_on=data.get("on", False), last_modified=last_modified)


@dataclass
class Flag:
    """Represents a LaunchDarkly feature flag."""

    key: str
    name: str
    archived: bool
    temporary: bool
    creation_date: datetime.datetime
    maintainer: Maintainer
    environments: dict[str, Environment]
    # Fields for "ready to archive" analysis
    code_references_count: int = 0  # From expand=codeReferences in flags API
    last_requested: datetime.datetime | None = None  # From flag-statuses API

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Flag":
        """Create Flag from API response dictionary."""
        creation_date_ms = data.get("creationDate", 0)
        creation_date = datetime.datetime.fromtimestamp(creation_date_ms / 1000.0)

        maintainer_data = data.get("_maintainer", {})
        maintainer = Maintainer.from_dict(maintainer_data)

        environments_data = data.get("environments", {})
        environments = {name: Environment.from_dict(name, env_data) for name, env_data in environments_data.items()}

        # Parse code references count from expanded response
        code_refs_data = data.get("_codeReferences", {})
        code_references_count = code_refs_data.get("total", 0) if code_refs_data else 0

        return cls(
            key=data["key"],
            name=data.get("name", ""),
            archived=data.get("archived", False),
            temporary=data.get("temporary", False),
            creation_date=creation_date,
            maintainer=maintainer,
            environments=environments,
            code_references_count=code_references_count,
            # last_requested is set separately from flag-statuses API
        )

    @property
    def most_recent_modification(self) -> datetime.datetime | None:
        """Get the most recent modification date across all environments."""
        if not self.environments:
            return None

        return max(env.last_modified for env in self.environments.values())

    def is_inactive_since(self, threshold: datetime.datetime) -> bool:
        """Check if flag has been inactive (not modified) since the given threshold."""
        if not self.environments:
            return True

        return all(env.last_modified < threshold for env in self.environments.values())

    def is_ready_to_archive(self, min_age_days: int = 30, eval_window_days: int = 7) -> bool:
        """
        Check if flag meets 'ready to archive' criteria.

        A flag is ready to archive when:
        - It is temporary (not permanent)
        - It is not already archived
        - It is older than min_age_days
        - It has no code references
        - It has not been requested in the past eval_window_days

        Args:
            min_age_days: Minimum age in days (default: 30)
            eval_window_days: Evaluation window in days (default: 7)

        Returns:
            True if flag meets all criteria
        """
        # Must be temporary and not archived
        if not self.temporary or self.archived:
            return False

        now = datetime.datetime.now()

        # Must be older than min_age_days
        age = now - self.creation_date
        if age.days < min_age_days:
            return False

        # Must have no code references
        if self.code_references_count > 0:
            return False

        # Must not have been requested recently
        if self.last_requested is not None:
            request_age = now - self.last_requested
            if request_age.days < eval_window_days:
                return False

        return True
