"""
Tests for deprecated aliases in swarm.runtime.stepwise.routing.

`route_step_unified` is a backwards-compat alias for the canonical
`route_step`. It is scheduled for removal in v4.0, so touching it must warn
loudly enough to be seen (FutureWarning is shown by default; DeprecationWarning
is not) while continuing to work for existing callers.
"""

import warnings

import pytest
from swarm.runtime.stepwise import routing


class TestDeprecationWarning:
    """Tests that touching a deprecated alias warns."""

    def test_attribute_access_warns(self):
        """Reading the alias off the module emits FutureWarning."""
        with pytest.warns(FutureWarning):
            routing.route_step_unified

    def test_from_import_warns(self):
        """`from ... import route_step_unified` emits FutureWarning."""
        with pytest.warns(FutureWarning):
            from swarm.runtime.stepwise.routing import route_step_unified  # noqa: F401

    def test_warning_names_the_replacement(self):
        """The warning tells the caller what to use instead."""
        with pytest.warns(FutureWarning) as record:
            routing.route_step_unified

        message = str(record[0].message)
        assert "route_step" in message
        assert "deprecated" in message.lower()

    def test_warning_names_the_removal_version(self):
        """The warning states when the alias goes away."""
        with pytest.warns(FutureWarning) as record:
            routing.route_step_unified

        assert "v4.0" in str(record[0].message)

    def test_uses_futurewarning_not_deprecationwarning(self):
        """FutureWarning is visible by default; DeprecationWarning is not.

        A DeprecationWarning here would be silently swallowed for the very
        callers who need to migrate.
        """
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            routing.route_step_unified

        assert caught
        assert all(issubclass(w.category, FutureWarning) for w in caught)


class TestBackwardsCompatibility:
    """Tests that the alias still works while deprecated."""

    def test_alias_resolves_to_canonical_function(self):
        """The alias is the canonical function, not a copy."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            alias = routing.route_step_unified

        assert alias is routing.route_step

    def test_alias_is_still_exported(self):
        """The alias remains in __all__ until it is removed in v4.0."""
        assert "route_step_unified" in routing.__all__

    def test_star_import_still_provides_alias(self):
        """`import *` keeps working for existing callers."""
        namespace: dict = {}

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            exec("from swarm.runtime.stepwise.routing import *", namespace)

        assert "route_step_unified" in namespace
        assert "route_step" in namespace


class TestCanonicalNamesAreUnaffected:
    """Tests that the deprecation hook does not disturb real attributes."""

    def test_canonical_route_step_does_not_warn(self):
        """Using the canonical name is silent."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            routing.route_step

        assert not [w for w in caught if issubclass(w.category, FutureWarning)]

    def test_routing_outcome_does_not_warn(self):
        """Other real exports are untouched by module __getattr__."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            routing.RoutingOutcome

        assert not [w for w in caught if issubclass(w.category, FutureWarning)]

    def test_unknown_attribute_still_raises(self):
        """A genuine typo is an AttributeError, not a silent None."""
        with pytest.raises(AttributeError, match="no attribute"):
            routing.definitely_not_a_real_export


class TestAliasRegistry:
    """Tests for the alias table itself."""

    def test_every_alias_points_at_a_real_export(self):
        """A deprecated alias must resolve to something that exists.

        Otherwise the alias raises KeyError instead of warning-and-working.
        """
        for deprecated, canonical in routing._DEPRECATED_ALIASES.items():
            assert hasattr(routing, canonical), (
                f"alias {deprecated} points at missing {canonical}"
            )

    def test_aliases_do_not_shadow_real_exports(self):
        """A deprecated name must not also be a real module attribute.

        Module __getattr__ only fires for names that are *not* found normally,
        so a shadowed alias would never warn.
        """
        for deprecated in routing._DEPRECATED_ALIASES:
            assert deprecated not in vars(routing), (
                f"{deprecated} is defined directly, so its deprecation never fires"
            )
