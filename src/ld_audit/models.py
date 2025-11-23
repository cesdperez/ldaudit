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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Flag":
        """Create Flag from API response dictionary."""
        creation_date_ms = data.get("creationDate", 0)
        creation_date = datetime.datetime.fromtimestamp(creation_date_ms / 1000.0)

        maintainer_data = data.get("_maintainer", {})
        maintainer = Maintainer.from_dict(maintainer_data)

        environments_data = data.get("environments", {})
        environments = {name: Environment.from_dict(name, env_data) for name, env_data in environments_data.items()}

        return cls(
            key=data["key"],
            name=data.get("name", ""),
            archived=data.get("archived", False),
            temporary=data.get("temporary", False),
            creation_date=creation_date,
            maintainer=maintainer,
            environments=environments,
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
