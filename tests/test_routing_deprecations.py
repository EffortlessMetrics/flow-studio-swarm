"""
Tests for deprecated routing aliases (issue #220).

Repo policy (.claude/rules/governance/deprecation.md) requires a deprecated
surface to warn and to name its replacement before removal. `route_step_unified`
is a pure alias for `route_step`, scheduled for removal in v4.0.
"""

import warnings

import pytest
from swarm.runtime.stepwise import routing


class TestRouteStepUnifiedAlias:
    """`route_step_unified` still works, but warns and names its replacement."""

    def test_alias_resolves_to_canonical_function(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            alias = routing.route_step_unified

        assert alias is routing.route_step

    def test_attribute_access_warns(self):
        with pytest.warns(FutureWarning, match="route_step_unified is deprecated"):
            routing.route_step_unified

    def test_warning_names_the_replacement_and_removal_version(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            routing.route_step_unified

        assert len(caught) == 1
        message = str(caught[0].message)
        assert "route_step" in message
        assert "v4.0" in message

    def test_from_import_warns(self):
        """`from ... import route_step_unified` goes through module __getattr__."""
        with pytest.warns(FutureWarning):
            from swarm.runtime.stepwise.routing import (  # noqa: F401
                route_step_unified,
            )

    def test_alias_is_still_discoverable(self):
        """dir() lists the alias so existing tooling can still find it."""
        assert "route_step_unified" in dir(routing)
        assert "route_step_unified" in routing.__all__


class TestCanonicalSurfaceIsQuiet:
    """The canonical API must not emit deprecation noise."""

    def test_route_step_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            assert routing.route_step is not None
            assert routing.RoutingOutcome is not None

    def test_unknown_attribute_raises_attribute_error(self):
        """__getattr__ must not swallow genuine typos."""
        with pytest.raises(AttributeError, match="no attribute 'route_step_typo'"):
            routing.route_step_typo


class TestNoInternalUseOfDeprecatedAlias:
    """Production code must use the canonical name (issue #220, step 2)."""

    def test_alias_not_referenced_in_swarm_package(self):
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[1]
        alias_module = repo_root / "swarm" / "runtime" / "stepwise" / "routing" / "__init__.py"

        offenders = []
        for path in (repo_root / "swarm").rglob("*.py"):
            if path == alias_module:
                continue  # The alias is defined here.
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "route_step_unified" in text:
                offenders.append(str(path.relative_to(repo_root)))

        assert not offenders, (
            "Production code should call route_step, not the deprecated "
            f"route_step_unified alias: {offenders}"
        )
