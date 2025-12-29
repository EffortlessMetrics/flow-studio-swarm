"""Tests for pack registry and configuration resolution."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from swarm.config.pack_registry import (
    Pack,
    EngineConfig,
    FeaturesConfig,
    RuntimeConfig,
    PackResolver,
    load_pack_from_file,
    load_baseline_pack,
    get_baseline_pack_path,
    resolve_pack_config,
)


class TestPackLoading:
    """Tests for pack file loading."""

    def test_load_baseline_pack_exists(self):
        """Baseline pack should exist and load successfully."""
        pack = load_baseline_pack()
        assert pack is not None
        assert pack.id == "baseline"
        assert pack.version == "1.0"

    def test_baseline_pack_has_engines(self):
        """Baseline pack should have engine configuration."""
        pack = load_baseline_pack()
        assert "claude" in pack.engines
        assert pack.engines["claude"].mode == "stub"
        assert pack.engines["claude"].execution == "legacy"

    def test_baseline_pack_has_features(self):
        """Baseline pack should have feature flags."""
        pack = load_baseline_pack()
        assert pack.features.stepwise_execution is True
        assert pack.features.write_receipts is True

    def test_baseline_pack_has_runtime(self):
        """Baseline pack should have runtime settings."""
        pack = load_baseline_pack()
        assert pack.runtime.context_budget_chars == 200000
        assert pack.runtime.timeout_seconds == 30

    def test_load_nonexistent_file_returns_none(self, tmp_path):
        """Loading a nonexistent file should return None."""
        result = load_pack_from_file(tmp_path / "nonexistent.yaml")
        assert result is None

    def test_load_empty_pack_returns_defaults(self, tmp_path):
        """Empty pack file should return Pack with defaults."""
        pack_file = tmp_path / "pack.yaml"
        pack_file.write_text("")
        pack = load_pack_from_file(pack_file)
        assert pack is not None
        assert pack.version == "1.0"
        assert pack.engines == {}

    def test_load_pack_with_engine_override(self, tmp_path):
        """Pack with engine override should load correctly."""
        pack_file = tmp_path / "pack.yaml"
        pack_file.write_text("""
version: "1.0"
engines:
  claude:
    mode: sdk
    execution: session
""")
        pack = load_pack_from_file(pack_file)
        assert pack is not None
        assert "claude" in pack.engines
        assert pack.engines["claude"].mode == "sdk"
        assert pack.engines["claude"].execution == "session"


class TestPackResolution:
    """Tests for pack resolution with provenance."""

    def test_baseline_provides_defaults(self):
        """Resolver should use baseline when no overrides present."""
        resolver = PackResolver(repo_root=None)
        result = resolver.resolve()

        assert result.config.get("engines.claude.mode") == "stub"
        assert result.provenance["engines.claude.mode"].source == "baseline"

    def test_env_overrides_baseline(self):
        """Environment variables should override baseline."""
        with patch.dict(os.environ, {"SWARM_CLAUDE_MODE": "sdk"}):
            resolver = PackResolver(repo_root=None)
            result = resolver.resolve()

            assert result.config.get("engines.claude.mode") == "sdk"
            assert result.provenance["engines.claude.mode"].source == "env"
            assert result.provenance["engines.claude.mode"].path == "SWARM_CLAUDE_MODE"

    def test_cli_overrides_env(self):
        """CLI overrides should take highest priority."""
        with patch.dict(os.environ, {"SWARM_CLAUDE_MODE": "sdk"}):
            resolver = PackResolver(
                repo_root=None,
                cli_overrides={"engines.claude.mode": "cli"}
            )
            result = resolver.resolve()

            assert result.config.get("engines.claude.mode") == "cli"
            assert result.provenance["engines.claude.mode"].source == "cli"

    def test_repo_pack_overrides_baseline(self, tmp_path):
        """Repo pack should override baseline but not env."""
        # Create repo pack
        swarm_dir = tmp_path / ".swarm"
        swarm_dir.mkdir()
        pack_file = swarm_dir / "pack.yaml"
        pack_file.write_text("""
version: "1.0"
engines:
  claude:
    mode: sdk
    execution: session
""")

        resolver = PackResolver(repo_root=tmp_path)
        result = resolver.resolve()

        assert result.config.get("engines.claude.mode") == "sdk"
        assert result.config.get("engines.claude.execution") == "session"
        assert result.provenance["engines.claude.mode"].source == "repo"

    def test_env_boolean_parsing(self):
        """Environment booleans should be parsed correctly."""
        with patch.dict(os.environ, {"SWARM_FEATURE_STEPWISE_EXECUTION": "false"}):
            resolver = PackResolver(repo_root=None)
            result = resolver.resolve()

            assert result.config.get("features.stepwise_execution") is False

    def test_env_integer_parsing(self):
        """Environment integers should be parsed correctly."""
        with patch.dict(os.environ, {"SWARM_CONTEXT_BUDGET_CHARS": "500000"}):
            resolver = PackResolver(repo_root=None)
            result = resolver.resolve()

            assert result.config.get("runtime.context_budget_chars") == 500000


class TestConvenienceFunction:
    """Tests for the resolve_pack_config convenience function."""

    def test_resolve_pack_config_returns_result(self):
        """resolve_pack_config should return ResolvedConfig."""
        result = resolve_pack_config()
        assert result is not None
        assert isinstance(result.config, dict)
        assert isinstance(result.provenance, dict)

    def test_resolve_pack_config_with_cli_overrides(self):
        """resolve_pack_config should accept CLI overrides."""
        result = resolve_pack_config(
            cli_overrides={"engines.claude.mode": "test"}
        )
        assert result.config.get("engines.claude.mode") == "test"
