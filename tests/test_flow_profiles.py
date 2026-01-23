"""Tests for flow profile system.

This module tests the profile_registry module which provides functionality
for saving, loading, listing, and comparing swarm configuration profiles.
Profiles are portable snapshots that capture flows.yaml, flow configs,
and agent configs in a single file.
"""

# Import the profile registry
import sys
from pathlib import Path

import pytest

import yaml

_SWARM_ROOT = Path(__file__).resolve().parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from swarm.config.profile_registry import (
    PROFILE_EXTENSION,
    ConfigEntry,
    ProfileMeta,
    ProfileRegistry,
    create_profile,
    profile_from_dict,
    profile_to_dict,
)


class TestProfileMeta:
    """Test ProfileMeta dataclass behavior."""

    def test_profile_meta_required_fields(self):
        """ProfileMeta should require id and label fields."""
        meta = ProfileMeta(id="test-id", label="Test Label")
        assert meta.id == "test-id"
        assert meta.label == "Test Label"
        assert meta.description == ""  # default
        assert meta.created_at is None  # default
        assert meta.created_by is None  # default

    def test_profile_meta_all_fields(self):
        """ProfileMeta should accept all optional fields."""
        meta = ProfileMeta(
            id="full-id",
            label="Full Label",
            description="A complete description",
            created_at="2025-01-01T00:00:00Z",
            created_by="test-user",
        )
        assert meta.id == "full-id"
        assert meta.label == "Full Label"
        assert meta.description == "A complete description"
        assert meta.created_at == "2025-01-01T00:00:00Z"
        assert meta.created_by == "test-user"


class TestConfigEntry:
    """Test ConfigEntry dataclass behavior."""

    def test_config_entry_creation(self):
        """ConfigEntry should store key, path, and yaml content."""
        entry = ConfigEntry(
            key="signal",
            path="swarm/config/flows/signal.yaml",
            yaml="key: signal\nlabel: Signal Flow\n",
        )
        assert entry.key == "signal"
        assert entry.path == "swarm/config/flows/signal.yaml"
        assert "key: signal" in entry.yaml


class TestProfileRoundTrip:
    """Test that profiles can be saved and loaded without data loss."""

    def test_profile_roundtrip_serialization(self):
        """Test profile dict serialization is lossless."""
        # Create a profile with all fields
        profile = create_profile(
            profile_id="test-profile",
            label="Test Profile",
            description="A test profile for validation",
            flows_yaml="flows:\n  - key: signal\n",
            flow_configs=[
                ConfigEntry(
                    key="signal", path="swarm/config/flows/signal.yaml", yaml="key: signal\n"
                ),
            ],
            agent_configs=[
                ConfigEntry(
                    key="test-agent",
                    path="swarm/config/agents/test-agent.yaml",
                    yaml="key: test-agent\n",
                ),
            ],
        )

        # Round-trip through dict
        d = profile_to_dict(profile)
        restored = profile_from_dict(d)

        # Verify all fields match
        assert restored.meta.id == profile.meta.id
        assert restored.meta.label == profile.meta.label
        assert restored.meta.description == profile.meta.description
        assert restored.flows_yaml == profile.flows_yaml
        assert len(restored.flow_configs) == len(profile.flow_configs)
        assert len(restored.agent_configs) == len(profile.agent_configs)

    def test_profile_roundtrip_preserves_config_entries(self):
        """Test that config entries are preserved through serialization."""
        flow_config = ConfigEntry(
            key="build",
            path="swarm/config/flows/build.yaml",
            yaml="key: build\nsteps:\n  - test-author\n  - code-implementer\n",
        )
        agent_config = ConfigEntry(
            key="code-implementer",
            path="swarm/config/agents/code-implementer.yaml",
            yaml="name: code-implementer\nmodel: sonnet\n",
        )

        profile = create_profile(
            profile_id="config-test",
            label="Config Test",
            flow_configs=[flow_config],
            agent_configs=[agent_config],
        )

        d = profile_to_dict(profile)
        restored = profile_from_dict(d)

        # Verify flow configs
        assert len(restored.flow_configs) == 1
        assert restored.flow_configs[0].key == "build"
        assert restored.flow_configs[0].path == flow_config.path
        assert restored.flow_configs[0].yaml == flow_config.yaml

        # Verify agent configs
        assert len(restored.agent_configs) == 1
        assert restored.agent_configs[0].key == "code-implementer"
        assert restored.agent_configs[0].yaml == agent_config.yaml

    def test_profile_roundtrip_empty_configs(self):
        """Test profile with empty config lists serializes correctly."""
        profile = create_profile(
            profile_id="empty-configs",
            label="Empty Configs",
            flows_yaml="",
            flow_configs=[],
            agent_configs=[],
        )

        d = profile_to_dict(profile)
        restored = profile_from_dict(d)

        assert restored.meta.id == "empty-configs"
        assert restored.flows_yaml == ""
        assert restored.flow_configs == []
        assert restored.agent_configs == []

    def test_profile_to_dict_structure(self):
        """Test that profile_to_dict produces expected structure."""
        profile = create_profile(
            profile_id="struct-test",
            label="Structure Test",
            description="Testing dict structure",
            created_by="tester",
            flows_yaml="flows: []\n",
        )

        d = profile_to_dict(profile)

        # Verify top-level keys
        assert "meta" in d
        assert "flows_yaml" in d
        assert "flow_configs" in d
        assert "agent_configs" in d

        # Verify meta structure
        assert d["meta"]["id"] == "struct-test"
        assert d["meta"]["label"] == "Structure Test"
        assert d["meta"]["description"] == "Testing dict structure"
        assert d["meta"]["created_by"] == "tester"
        assert d["meta"]["created_at"] is not None


class TestProfileRegistry:
    """Test ProfileRegistry operations."""

    def test_save_and_load_profile(self, tmp_path):
        """Test saving and loading a profile from disk."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        profile = create_profile(
            profile_id="disk-test",
            label="Disk Test",
            description="Testing disk I/O",
        )

        # Save
        path = registry.save_profile(profile)
        assert path.exists()
        assert path.suffix == ".yaml"
        assert "disk-test" in path.name

        # Clear cache and reload
        registry.clear_cache()
        loaded = registry.load_profile("disk-test")

        assert loaded.meta.id == "disk-test"
        assert loaded.meta.label == "Disk Test"
        assert loaded.meta.description == "Testing disk I/O"

    def test_save_creates_directory(self, tmp_path):
        """Test that save_profile creates the profile directory if needed."""
        nested_dir = tmp_path / "nested" / "profile" / "dir"
        registry = ProfileRegistry(profile_dir=nested_dir)

        profile = create_profile(
            profile_id="nested-test",
            label="Nested Test",
        )

        path = registry.save_profile(profile)
        assert nested_dir.exists()
        assert path.exists()

    def test_list_profiles(self, tmp_path):
        """Test listing available profiles."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        # Create two profiles
        for i in range(2):
            profile = create_profile(
                profile_id=f"profile-{i}",
                label=f"Profile {i}",
            )
            registry.save_profile(profile)

        profiles = registry.list_profiles()
        assert len(profiles) == 2
        ids = [p.id for p in profiles]
        assert "profile-0" in ids
        assert "profile-1" in ids

    def test_list_profiles_empty_directory(self, tmp_path):
        """Test listing profiles in empty directory returns empty list."""
        registry = ProfileRegistry(profile_dir=tmp_path)
        profiles = registry.list_profiles()
        assert profiles == []

    def test_list_profiles_nonexistent_directory(self, tmp_path):
        """Test listing profiles when directory does not exist."""
        nonexistent = tmp_path / "does_not_exist"
        registry = ProfileRegistry(profile_dir=nonexistent)
        profiles = registry.list_profiles()
        assert profiles == []

    def test_profile_not_found(self, tmp_path):
        """Test loading non-existent profile raises error."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            registry.load_profile("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_profile_exists(self, tmp_path):
        """Test profile_exists method."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        assert registry.profile_exists("missing") is False

        profile = create_profile(profile_id="exists-test", label="Exists Test")
        registry.save_profile(profile)

        assert registry.profile_exists("exists-test") is True
        assert registry.profile_exists("still-missing") is False

    def test_delete_profile(self, tmp_path):
        """Test deleting a profile."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        profile = create_profile(profile_id="to-delete", label="To Delete")
        path = registry.save_profile(profile)
        assert path.exists()

        # Delete should return True and remove file
        result = registry.delete_profile("to-delete")
        assert result is True
        assert not path.exists()

        # Deleting again should return False
        result = registry.delete_profile("to-delete")
        assert result is False

    def test_delete_nonexistent_profile(self, tmp_path):
        """Test deleting a profile that does not exist."""
        registry = ProfileRegistry(profile_dir=tmp_path)
        result = registry.delete_profile("nonexistent")
        assert result is False

    def test_cache_behavior(self, tmp_path):
        """Test that profiles are cached after loading."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        profile = create_profile(profile_id="cache-test", label="Cache Test")
        registry.save_profile(profile)

        # Load profile (should cache it)
        registry.load_profile("cache-test")

        # Modify the file on disk
        profile_path = tmp_path / f"cache-test{PROFILE_EXTENSION}"
        with open(profile_path, "w") as f:
            yaml.safe_dump({"meta": {"id": "cache-test", "label": "Modified"}}, f)

        # Load again (should return cached version)
        loaded2 = registry.load_profile("cache-test")
        assert loaded2.meta.label == "Cache Test"  # Original, not modified

        # Clear cache and load again
        registry.clear_cache()
        loaded3 = registry.load_profile("cache-test")
        assert loaded3.meta.label == "Modified"  # Now sees the modification

    def test_save_updates_cache(self, tmp_path):
        """Test that saving a profile updates the cache."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        profile1 = create_profile(profile_id="update-test", label="Version 1")
        registry.save_profile(profile1)

        # Load to populate cache
        loaded1 = registry.load_profile("update-test")
        assert loaded1.meta.label == "Version 1"

        # Save updated profile
        profile2 = create_profile(profile_id="update-test", label="Version 2")
        registry.save_profile(profile2)

        # Load should return updated version from cache
        loaded2 = registry.load_profile("update-test")
        assert loaded2.meta.label == "Version 2"


class TestProfileDiff:
    """Test profile comparison functionality."""

    def test_identical_profiles_have_no_diff(self):
        """Two identical profiles should show no differences."""
        profile_a = create_profile(
            profile_id="a",
            label="A",
            flows_yaml="flows: []\n",
        )
        profile_b = create_profile(
            profile_id="b",
            label="B",
            flows_yaml="flows: []\n",
        )

        # Content comparison (excluding meta)
        assert profile_a.flows_yaml == profile_b.flows_yaml
        assert profile_a.flow_configs == profile_b.flow_configs
        assert profile_a.agent_configs == profile_b.agent_configs

    def test_different_flows_yaml(self):
        """Profiles with different flows_yaml should differ."""
        profile_a = create_profile(
            profile_id="a",
            label="A",
            flows_yaml="flows:\n  - signal\n",
        )
        profile_b = create_profile(
            profile_id="b",
            label="B",
            flows_yaml="flows:\n  - signal\n  - build\n",
        )

        assert profile_a.flows_yaml != profile_b.flows_yaml

    def test_different_flow_configs(self):
        """Profiles with different flow configs should differ."""
        profile_a = create_profile(
            profile_id="a",
            label="A",
            flow_configs=[
                ConfigEntry(key="signal", path="p1", yaml="v1"),
            ],
        )
        profile_b = create_profile(
            profile_id="b",
            label="B",
            flow_configs=[
                ConfigEntry(key="signal", path="p1", yaml="v2"),  # Different yaml
            ],
        )

        assert profile_a.flow_configs[0].yaml != profile_b.flow_configs[0].yaml

    def test_different_agent_counts(self):
        """Profiles with different numbers of agents should differ."""
        profile_a = create_profile(
            profile_id="a",
            label="A",
            agent_configs=[
                ConfigEntry(key="agent1", path="p1", yaml="v1"),
            ],
        )
        profile_b = create_profile(
            profile_id="b",
            label="B",
            agent_configs=[
                ConfigEntry(key="agent1", path="p1", yaml="v1"),
                ConfigEntry(key="agent2", path="p2", yaml="v2"),
            ],
        )

        assert len(profile_a.agent_configs) != len(profile_b.agent_configs)


class TestCreateProfile:
    """Test the create_profile factory function."""

    def test_create_profile_sets_timestamp(self):
        """create_profile should automatically set created_at timestamp."""
        profile = create_profile(
            profile_id="timestamp-test",
            label="Timestamp Test",
        )

        assert profile.meta.created_at is not None
        assert profile.meta.created_at.endswith("Z")  # UTC marker

    def test_create_profile_with_created_by(self):
        """create_profile should accept created_by parameter."""
        profile = create_profile(
            profile_id="author-test",
            label="Author Test",
            created_by="test-author",
        )

        assert profile.meta.created_by == "test-author"

    def test_create_profile_defaults(self):
        """create_profile should have sensible defaults."""
        profile = create_profile(
            profile_id="defaults-test",
            label="Defaults Test",
        )

        assert profile.meta.description == ""
        assert profile.flows_yaml == ""
        assert profile.flow_configs == []
        assert profile.agent_configs == []


class TestProfileFromDict:
    """Test profile_from_dict parsing edge cases."""

    def test_parse_empty_dict(self):
        """profile_from_dict should handle empty dict gracefully."""
        profile = profile_from_dict({})

        assert profile.meta.id == ""
        assert profile.meta.label == ""
        assert profile.flows_yaml == ""
        assert profile.flow_configs == []
        assert profile.agent_configs == []

    def test_parse_partial_meta(self):
        """profile_from_dict should handle partial meta gracefully."""
        data = {
            "meta": {"id": "partial", "label": "Partial"},
            # Missing description, created_at, created_by
        }
        profile = profile_from_dict(data)

        assert profile.meta.id == "partial"
        assert profile.meta.label == "Partial"
        assert profile.meta.description == ""
        assert profile.meta.created_at is None

    def test_parse_with_extra_fields(self):
        """profile_from_dict should ignore unknown fields."""
        data = {
            "meta": {"id": "extra", "label": "Extra", "unknown_field": "ignored"},
            "flows_yaml": "flows: []\n",
            "extra_top_level": "also ignored",
        }
        profile = profile_from_dict(data)

        assert profile.meta.id == "extra"
        assert profile.flows_yaml == "flows: []\n"


class TestRegistrySingleton:
    """Test ProfileRegistry singleton behavior."""

    def test_get_instance_returns_same_object(self):
        """get_instance should return the same registry instance."""
        ProfileRegistry.reset()  # Clean state

        instance1 = ProfileRegistry.get_instance()
        instance2 = ProfileRegistry.get_instance()

        assert instance1 is instance2

        ProfileRegistry.reset()  # Cleanup

    def test_reset_clears_singleton(self):
        """reset should clear the singleton instance."""
        ProfileRegistry.reset()  # Clean state

        instance1 = ProfileRegistry.get_instance()
        ProfileRegistry.reset()
        instance2 = ProfileRegistry.get_instance()

        assert instance1 is not instance2

        ProfileRegistry.reset()  # Cleanup


class TestYAMLPersistence:
    """Test YAML file format and persistence details."""

    def test_profile_file_is_valid_yaml(self, tmp_path):
        """Saved profile files should be valid YAML."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        profile = create_profile(
            profile_id="yaml-test",
            label="YAML Test",
            description="Testing YAML format",
            flows_yaml="flows:\n  - signal\n  - build\n",
        )

        path = registry.save_profile(profile)

        # Read and parse as YAML
        with open(path) as f:
            data = yaml.safe_load(f)

        assert data["meta"]["id"] == "yaml-test"
        assert data["flows_yaml"] == "flows:\n  - signal\n  - build\n"

    def test_profile_file_extension(self, tmp_path):
        """Profile files should use the correct extension."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        profile = create_profile(profile_id="ext-test", label="Extension Test")
        path = registry.save_profile(profile)

        assert path.name == f"ext-test{PROFILE_EXTENSION}"

    def test_special_characters_in_yaml(self, tmp_path):
        """Profiles with special YAML characters should be handled correctly."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        profile = create_profile(
            profile_id="special-chars",
            label="Special: Characters & More",
            description="Testing 'quotes' and \"double quotes\" and colons: here",
            flows_yaml="# Comment\nflows:\n  - name: 'quoted'\n",
        )

        registry.save_profile(profile)
        registry.clear_cache()
        loaded = registry.load_profile("special-chars")

        assert loaded.meta.label == "Special: Characters & More"
        assert "quotes" in loaded.meta.description
        assert loaded.flows_yaml == "# Comment\nflows:\n  - name: 'quoted'\n"

    def test_multiline_yaml_content(self, tmp_path):
        """Profiles should preserve multiline YAML content."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        multiline_yaml = """key: value
nested:
  items:
    - first
    - second
  config:
    option1: true
    option2: false
"""

        profile = create_profile(
            profile_id="multiline",
            label="Multiline",
            flows_yaml=multiline_yaml,
        )

        registry.save_profile(profile)
        registry.clear_cache()
        loaded = registry.load_profile("multiline")

        assert loaded.flows_yaml == multiline_yaml


class TestProfileIntegration:
    """Integration tests for complete profile workflows."""

    def test_full_profile_workflow(self, tmp_path):
        """Test complete create -> save -> list -> load -> delete workflow."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        # Create
        profile = create_profile(
            profile_id="workflow-test",
            label="Workflow Test",
            description="Integration test profile",
            flows_yaml="flows:\n  - signal\n",
            flow_configs=[
                ConfigEntry(key="signal", path="flows/signal.yaml", yaml="key: signal\n"),
            ],
            agent_configs=[
                ConfigEntry(key="agent1", path="agents/agent1.yaml", yaml="name: agent1\n"),
                ConfigEntry(key="agent2", path="agents/agent2.yaml", yaml="name: agent2\n"),
            ],
        )

        # Save
        path = registry.save_profile(profile)
        assert path.exists()

        # List
        profiles = registry.list_profiles()
        assert len(profiles) == 1
        assert profiles[0].id == "workflow-test"

        # Load
        loaded = registry.load_profile("workflow-test")
        assert loaded.meta.id == "workflow-test"
        assert loaded.meta.label == "Workflow Test"
        assert len(loaded.flow_configs) == 1
        assert len(loaded.agent_configs) == 2

        # Delete
        result = registry.delete_profile("workflow-test")
        assert result is True
        assert not path.exists()

        # List after delete
        profiles = registry.list_profiles()
        assert len(profiles) == 0

    def test_multiple_profiles_coexist(self, tmp_path):
        """Test that multiple profiles can coexist in the same directory."""
        registry = ProfileRegistry(profile_dir=tmp_path)

        # Create three profiles
        for i in range(3):
            profile = create_profile(
                profile_id=f"coexist-{i}",
                label=f"Coexist {i}",
                flows_yaml=f"version: {i}\n",
            )
            registry.save_profile(profile)

        # All should be listable
        profiles = registry.list_profiles()
        assert len(profiles) == 3

        # All should be independently loadable
        for i in range(3):
            loaded = registry.load_profile(f"coexist-{i}")
            assert loaded.flows_yaml == f"version: {i}\n"

        # Delete one, others remain
        registry.delete_profile("coexist-1")
        profiles = registry.list_profiles()
        assert len(profiles) == 2
        ids = [p.id for p in profiles]
        assert "coexist-0" in ids
        assert "coexist-2" in ids
        assert "coexist-1" not in ids
