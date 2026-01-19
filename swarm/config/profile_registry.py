"""
profile_registry.py - Load, save, and manage swarm profiles

Profiles are self-contained snapshots of swarm configuration that can be
exported, shared, and imported. They capture flows.yaml, flow configs,
and agent configs in a single portable file.

Usage:
    from swarm.config.profile_registry import list_profiles, load_profile, save_profile
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml

from swarm.utils.yaml_utils import load_yaml
from swarm.config.flow_registry import ContextBudgetOverride

_CONFIG_DIR = Path(__file__).parent
PROFILE_DIR = Path(__file__).parent.parent / "profiles"
PROFILE_EXTENSION = ".swarm_profile.yaml"
CURRENT_PROFILE_FILE = PROFILE_DIR / ".current_profile"


def _utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class CurrentProfileInfo:
    """Info about the currently loaded profile."""
    id: str
    label: str
    loaded_at: str
    source_branch: Optional[str] = None


@dataclass
class ProfileMeta:
    """Metadata for a swarm profile."""
    id: str
    label: str
    description: str = ""
    created_at: Optional[str] = None
    created_by: Optional[str] = None


@dataclass
class ConfigEntry:
    """A single config file entry (flow or agent)."""
    key: str
    path: str
    yaml: str


@dataclass
class RuntimeSettings:
    """Runtime configuration overrides stored in a profile (v2.4.0).

    Allows profiles to customize execution behavior without modifying
    the global runtime.yaml configuration.
    """
    context_budgets: Optional[ContextBudgetOverride] = None
    # Future: timeout_settings, engine_preferences, etc.


@dataclass
class Profile:
    """A complete swarm profile."""
    meta: ProfileMeta
    flows_yaml: str
    flow_configs: List[ConfigEntry] = field(default_factory=list)
    agent_configs: List[ConfigEntry] = field(default_factory=list)
    runtime_settings: Optional[RuntimeSettings] = None  # NEW in v2.4.0


class ProfileRegistry:
    """Registry for managing swarm profiles."""

    _instance: Optional["ProfileRegistry"] = None

    def __init__(self, profile_dir: Path = PROFILE_DIR):
        self._profile_dir = profile_dir
        self._profiles_cache: Dict[str, Profile] = {}

    @classmethod
    def get_instance(cls, profile_dir: Path = PROFILE_DIR) -> "ProfileRegistry":
        """Get singleton instance of the registry."""
        if cls._instance is None:
            cls._instance = cls(profile_dir)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton for testing."""
        cls._instance = None

    @property
    def profile_dir(self) -> Path:
        """Return the profile directory path."""
        return self._profile_dir

    @property
    def current_profile_file(self) -> Path:
        """Path to the marker file for the active profile."""
        return self._profile_dir / CURRENT_PROFILE_FILE.name

    def list_profiles(self) -> List[ProfileMeta]:
        """List all available profiles."""
        profiles: List[ProfileMeta] = []

        if not self._profile_dir.exists():
            return profiles

        for profile_file in sorted(self._profile_dir.glob(f"*{PROFILE_EXTENSION}")):
            try:
                with open(profile_file) as f:
                    data = load_yaml(f)

                if data and "meta" in data:
                    meta = _parse_profile_meta(data["meta"])
                    profiles.append(meta)
            except (yaml.YAMLError, KeyError, TypeError):
                # Skip invalid profile files
                continue

        return profiles

    def load_profile(self, profile_id: str) -> Profile:
        """Load a profile by ID."""
        # Check cache first
        if profile_id in self._profiles_cache:
            return self._profiles_cache[profile_id]

        profile_path = self._get_profile_path(profile_id)

        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile_id}")

        with open(profile_path) as f:
            data = load_yaml(f)

        profile = profile_from_dict(data)
        self._profiles_cache[profile_id] = profile
        return profile

    def save_profile(self, profile: Profile) -> Path:
        """Save a profile to disk. Returns the path."""
        # Ensure directory exists
        self._profile_dir.mkdir(parents=True, exist_ok=True)

        profile_path = self._get_profile_path(profile.meta.id)
        data = profile_to_dict(profile)

        with open(profile_path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

        # Update cache
        self._profiles_cache[profile.meta.id] = profile

        return profile_path

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile by ID. Returns True if deleted."""
        profile_path = self._get_profile_path(profile_id)

        if profile_path.exists():
            profile_path.unlink()
            self._profiles_cache.pop(profile_id, None)
            return True

        return False

    def profile_exists(self, profile_id: str) -> bool:
        """Check if a profile exists."""
        return self._get_profile_path(profile_id).exists()

    def _get_profile_path(self, profile_id: str) -> Path:
        """Get the file path for a profile ID."""
        return self._profile_dir / f"{profile_id}{PROFILE_EXTENSION}"

    def clear_cache(self) -> None:
        """Clear the profile cache."""
        self._profiles_cache.clear()

    def get_current_profile(self) -> Optional[CurrentProfileInfo]:
        """Read current profile marker file. Returns None if not set."""
        marker = self.current_profile_file
        if not marker.exists():
            return None

        try:
            with open(marker) as f:
                data = load_yaml(f)

            if not data:
                return None

            return CurrentProfileInfo(
                id=data.get("id", ""),
                label=data.get("label", ""),
                loaded_at=data.get("loaded_at", ""),
                source_branch=data.get("source_branch"),
            )
        except (yaml.YAMLError, KeyError, TypeError):
            return None

    def set_current_profile(
        self,
        profile_id: str,
        label: str,
        source_branch: Optional[str] = None,
    ) -> None:
        """Write current profile marker file."""
        # Ensure profile directory exists
        self._profile_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "id": profile_id,
            "label": label,
            "loaded_at": _utc_now_iso(),
            "source_branch": source_branch,
        }

        with open(self.current_profile_file, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    def clear_current_profile(self) -> None:
        """Remove current profile marker."""
        marker = self.current_profile_file
        if marker.exists():
            marker.unlink()


def _parse_profile_meta(data: Dict[str, Any]) -> ProfileMeta:
    """Parse ProfileMeta from dict."""
    return ProfileMeta(
        id=data.get("id", ""),
        label=data.get("label", ""),
        description=data.get("description", ""),
        created_at=data.get("created_at"),
        created_by=data.get("created_by"),
    )


def _parse_config_entry(data: Dict[str, Any]) -> ConfigEntry:
    """Parse ConfigEntry from dict."""
    return ConfigEntry(
        key=data.get("key", ""),
        path=data.get("path", ""),
        yaml=data.get("yaml", ""),
    )


def _runtime_settings_to_dict(settings: Optional[RuntimeSettings]) -> Optional[Dict[str, Any]]:
    """Convert RuntimeSettings to dict for YAML serialization."""
    if settings is None:
        return None
    result: Dict[str, Any] = {}
    if settings.context_budgets is not None:
        cb = settings.context_budgets
        result["context_budgets"] = {
            k: v for k, v in {
                "context_budget_chars": cb.context_budget_chars,
                "history_max_recent_chars": cb.history_max_recent_chars,
                "history_max_older_chars": cb.history_max_older_chars,
            }.items() if v is not None
        }
    return result if result else None


def profile_to_dict(profile: Profile) -> Dict[str, Any]:
    """Convert profile to dict for YAML serialization."""
    result: Dict[str, Any] = {
        "meta": {
            "id": profile.meta.id,
            "label": profile.meta.label,
            "description": profile.meta.description,
            "created_at": profile.meta.created_at,
            "created_by": profile.meta.created_by,
        },
        "flows_yaml": profile.flows_yaml,
        "flow_configs": [
            {
                "key": entry.key,
                "path": entry.path,
                "yaml": entry.yaml,
            }
            for entry in profile.flow_configs
        ],
        "agent_configs": [
            {
                "key": entry.key,
                "path": entry.path,
                "yaml": entry.yaml,
            }
            for entry in profile.agent_configs
        ],
    }
    # Only include runtime_settings if present (v2.4.0)
    runtime_dict = _runtime_settings_to_dict(profile.runtime_settings)
    if runtime_dict is not None:
        result["runtime_settings"] = runtime_dict
    return result


def _parse_runtime_settings(data: Optional[Dict[str, Any]]) -> Optional[RuntimeSettings]:
    """Parse RuntimeSettings from dict."""
    if data is None:
        return None

    context_budgets = None
    if "context_budgets" in data:
        cb_data = data["context_budgets"]
        context_budgets = ContextBudgetOverride(
            context_budget_chars=cb_data.get("context_budget_chars"),
            history_max_recent_chars=cb_data.get("history_max_recent_chars"),
            history_max_older_chars=cb_data.get("history_max_older_chars"),
        )

    return RuntimeSettings(context_budgets=context_budgets)


def profile_from_dict(data: Dict[str, Any]) -> Profile:
    """Parse a profile from dict."""
    meta = _parse_profile_meta(data.get("meta", {}))

    flow_configs = [
        _parse_config_entry(entry)
        for entry in data.get("flow_configs", [])
    ]

    agent_configs = [
        _parse_config_entry(entry)
        for entry in data.get("agent_configs", [])
    ]

    runtime_settings = _parse_runtime_settings(data.get("runtime_settings"))

    return Profile(
        meta=meta,
        flows_yaml=data.get("flows_yaml", ""),
        flow_configs=flow_configs,
        agent_configs=agent_configs,
        runtime_settings=runtime_settings,
    )


# Module-level convenience functions
def _get_registry() -> ProfileRegistry:
    """Get the singleton registry instance."""
    return ProfileRegistry.get_instance()


def list_profiles() -> List[ProfileMeta]:
    """List all available profiles."""
    return _get_registry().list_profiles()


def load_profile(profile_id: str) -> Profile:
    """Load a profile by ID."""
    return _get_registry().load_profile(profile_id)


def save_profile(profile: Profile) -> Path:
    """Save a profile to disk. Returns the path."""
    return _get_registry().save_profile(profile)


def delete_profile(profile_id: str) -> bool:
    """Delete a profile by ID. Returns True if deleted."""
    return _get_registry().delete_profile(profile_id)


def profile_exists(profile_id: str) -> bool:
    """Check if a profile exists."""
    return _get_registry().profile_exists(profile_id)


def create_profile(
    profile_id: str,
    label: str,
    description: str = "",
    created_by: Optional[str] = None,
    flows_yaml: str = "",
    flow_configs: Optional[List[ConfigEntry]] = None,
    agent_configs: Optional[List[ConfigEntry]] = None,
) -> Profile:
    """Create a new Profile object with timestamp."""
    return Profile(
        meta=ProfileMeta(
            id=profile_id,
            label=label,
            description=description,
            created_at=_utc_now_iso(),
            created_by=created_by,
        ),
        flows_yaml=flows_yaml,
        flow_configs=flow_configs or [],
        agent_configs=agent_configs or [],
    )


def get_current_profile() -> Optional[CurrentProfileInfo]:
    """Get currently loaded profile info."""
    return _get_registry().get_current_profile()


def set_current_profile(
    profile_id: str,
    label: str,
    source_branch: Optional[str] = None,
) -> None:
    """Set current profile marker."""
    return _get_registry().set_current_profile(profile_id, label, source_branch)
