"""Tests for context budget configuration and resolution.

Tests the ContextBudgetConfig, ContextBudgetOverride, and ContextBudgetResolver
classes introduced in v2.4.0.
"""

# Import path setup
import sys
from pathlib import Path

_SWARM_ROOT = Path(__file__).resolve().parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))


class TestContextBudgetDefaults:
    """Test that default budget values are correct."""

    def test_default_context_budget_chars(self):
        """Default context budget should be 200000 chars (~50k tokens)."""
        from swarm.config.runtime_config import get_context_budget_chars

        assert get_context_budget_chars() == 200000

    def test_default_history_max_recent_chars(self):
        """Default recent step budget should be 60000 chars (~15k tokens)."""
        from swarm.config.runtime_config import get_history_max_recent_chars

        assert get_history_max_recent_chars() == 60000

    def test_default_history_max_older_chars(self):
        """Default older step budget should be 10000 chars (~2.5k tokens)."""
        from swarm.config.runtime_config import get_history_max_older_chars

        assert get_history_max_older_chars() == 10000

    def test_budget_hierarchy_makes_sense(self):
        """Recent budget should be larger than older budget."""
        from swarm.config.runtime_config import (
            get_history_max_older_chars,
            get_history_max_recent_chars,
        )

        assert get_history_max_recent_chars() > get_history_max_older_chars()

    def test_total_budget_larger_than_individual(self):
        """Total budget should be larger than individual step budgets."""
        from swarm.config.runtime_config import (
            get_context_budget_chars,
            get_history_max_older_chars,
            get_history_max_recent_chars,
        )

        total = get_context_budget_chars()
        recent = get_history_max_recent_chars()
        older = get_history_max_older_chars()
        assert total > recent
        assert total > older


class TestContextBudgetConfig:
    """Test the ContextBudgetConfig dataclass."""

    def test_dataclass_creation(self):
        """ContextBudgetConfig can be created with all fields."""
        from swarm.config.runtime_config import ContextBudgetConfig

        config = ContextBudgetConfig(
            context_budget_chars=300000,
            history_max_recent_chars=100000,
            history_max_older_chars=15000,
            source="profile",
        )
        assert config.context_budget_chars == 300000
        assert config.history_max_recent_chars == 100000
        assert config.history_max_older_chars == 15000
        assert config.source == "profile"

    def test_default_source_is_default(self):
        """Default source should be 'default'."""
        from swarm.config.runtime_config import ContextBudgetConfig

        config = ContextBudgetConfig(
            context_budget_chars=200000,
            history_max_recent_chars=60000,
            history_max_older_chars=10000,
        )
        assert config.source == "default"


class TestContextBudgetResolver:
    """Test the ContextBudgetResolver cascade resolution."""

    def test_resolver_returns_defaults_without_overrides(self):
        """Resolver returns global defaults when no overrides exist."""
        from swarm.config.runtime_config import ContextBudgetResolver

        resolver = ContextBudgetResolver()
        result = resolver.resolve()
        assert result.context_budget_chars == 200000
        assert result.history_max_recent_chars == 60000
        assert result.history_max_older_chars == 10000
        assert result.source == "default"

    def test_resolver_with_flow_key_returns_defaults_if_no_flow_override(self):
        """Resolver returns defaults for a flow with no overrides."""
        from swarm.config.runtime_config import ContextBudgetResolver

        resolver = ContextBudgetResolver()
        result = resolver.resolve(flow_key="signal")
        # Should still be defaults since no flow override exists
        assert result.source == "default"

    def test_resolved_budgets_convenience_function(self):
        """get_resolved_context_budgets() should work as convenience wrapper."""
        from swarm.config.runtime_config import get_resolved_context_budgets

        result = get_resolved_context_budgets()
        assert result.context_budget_chars == 200000
        assert result.source == "default"

    def test_resolved_budgets_with_flow_key(self):
        """get_resolved_context_budgets() accepts flow_key parameter."""
        from swarm.config.runtime_config import get_resolved_context_budgets

        result = get_resolved_context_budgets(flow_key="build")
        assert isinstance(result.context_budget_chars, int)


class TestContextBudgetOverride:
    """Test the ContextBudgetOverride dataclass in flow_registry."""

    def test_override_dataclass_creation(self):
        """ContextBudgetOverride can be created with optional fields."""
        from swarm.config.flow_registry import ContextBudgetOverride

        override = ContextBudgetOverride(
            context_budget_chars=300000,
        )
        assert override.context_budget_chars == 300000
        assert override.history_max_recent_chars is None
        assert override.history_max_older_chars is None

    def test_override_merge_with_parent(self):
        """ContextBudgetOverride.merge_with() applies non-None values."""
        from swarm.config.flow_registry import ContextBudgetOverride

        parent = ContextBudgetOverride(
            context_budget_chars=200000,
            history_max_recent_chars=60000,
            history_max_older_chars=10000,
        )
        child = ContextBudgetOverride(
            context_budget_chars=300000,  # Override this
            # Leave others as None (inherit)
        )
        merged = child.merge_with(parent)
        assert merged.context_budget_chars == 300000  # Child value
        assert merged.history_max_recent_chars == 60000  # Parent value
        assert merged.history_max_older_chars == 10000  # Parent value

    def test_override_all_none_is_valid(self):
        """ContextBudgetOverride with all None is valid (inherit everything)."""
        from swarm.config.flow_registry import ContextBudgetOverride

        override = ContextBudgetOverride()
        assert override.context_budget_chars is None
        assert override.history_max_recent_chars is None
        assert override.history_max_older_chars is None


class TestEngineProfileContextBudgets:
    """Test that EngineProfile supports context_budgets field."""

    def test_engine_profile_has_context_budgets_field(self):
        """EngineProfile dataclass should have optional context_budgets."""
        from swarm.config.flow_registry import ContextBudgetOverride, EngineProfile

        profile = EngineProfile(
            engine="claude-step",
            mode="stub",
            context_budgets=ContextBudgetOverride(context_budget_chars=400000),
        )
        assert profile.context_budgets is not None
        assert profile.context_budgets.context_budget_chars == 400000

    def test_engine_profile_context_budgets_defaults_to_none(self):
        """EngineProfile context_budgets should default to None."""
        from swarm.config.flow_registry import EngineProfile

        profile = EngineProfile()
        assert profile.context_budgets is None


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_existing_accessors_still_work(self):
        """Existing get_*() functions should continue to work."""
        from swarm.config.runtime_config import (
            get_context_budget_chars,
            get_history_max_older_chars,
            get_history_max_recent_chars,
        )

        # These should return integers without errors
        assert isinstance(get_context_budget_chars(), int)
        assert isinstance(get_history_max_recent_chars(), int)
        assert isinstance(get_history_max_older_chars(), int)

    def test_values_are_reasonable(self):
        """Budget values should be within reasonable bounds."""
        from swarm.config.runtime_config import (
            get_context_budget_chars,
            get_history_max_older_chars,
            get_history_max_recent_chars,
        )

        # Minimum reasonable values
        assert get_context_budget_chars() >= 10000
        assert get_history_max_recent_chars() >= 1000
        assert get_history_max_older_chars() >= 500

        # Maximum reasonable values (shouldn't exceed context window)
        assert get_context_budget_chars() <= 1000000
        assert get_history_max_recent_chars() <= 500000
        assert get_history_max_older_chars() <= 100000
