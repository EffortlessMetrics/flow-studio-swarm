"""Smoke tests for MCP UX spec server internal functions.

These tests validate the helper functions in mcp_ux_spec.py work correctly
without spinning up a full MCP session.

NOTE: These tests require the 'mcp' optional dependency.
Install with: uv sync --extra mcp
"""

import sys
from pathlib import Path

import pytest

# Add swarm/tools to path for imports
SWARM_TOOLS = Path(__file__).parent.parent / "swarm" / "tools"
sys.path.insert(0, str(SWARM_TOOLS))

# Check if MCP is available
try:
    import mcp  # noqa: F401
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not MCP_AVAILABLE,
    reason="MCP package not installed. Install with: uv sync --extra mcp"
)


class TestMCPUXSpecHelpers:
    """Test internal helper functions from mcp_ux_spec.py."""

    def test_get_ux_manifest_returns_dict(self):
        """get_ux_manifest returns a dict with expected keys."""
        # Import the module (it will handle mcp import gracefully)
        from mcp_ux_spec import get_ux_manifest

        manifest = get_ux_manifest()

        assert isinstance(manifest, dict)
        # UX manifest should have these top-level keys
        expected_keys = {"layout_spec", "docs", "tests", "schemas"}
        assert expected_keys.issubset(set(manifest.keys())), (
            f"Missing keys: {expected_keys - set(manifest.keys())}"
        )

    def test_get_layout_screens_returns_list(self):
        """get_layout_screens returns a list of screen definitions."""
        from mcp_ux_spec import get_layout_screens

        screens = get_layout_screens()

        assert isinstance(screens, list)
        assert len(screens) > 0, "Should have at least one screen defined"

        # Each screen should have required fields
        for screen in screens:
            assert "id" in screen
            assert "route" in screen
            assert "regions" in screen
            assert "purpose" in screen

    def test_get_layout_screen_by_id_returns_screen_or_none(self):
        """get_layout_screen_by_id returns a screen dict or None."""
        from mcp_ux_spec import get_layout_screen_by_id, get_layout_screens

        screens = get_layout_screens()
        if screens:
            # Get a known screen ID
            first_screen_id = screens[0]["id"]
            screen = get_layout_screen_by_id(first_screen_id)

            assert screen is not None
            assert screen["id"] == first_screen_id

        # Unknown ID should return None
        unknown = get_layout_screen_by_id("nonexistent.screen.id")
        assert unknown is None

    def test_get_all_known_uiids_returns_list(self):
        """get_all_known_uiids returns a list of UIID strings."""
        from mcp_ux_spec import get_all_known_uiids

        uiids = get_all_known_uiids()

        assert isinstance(uiids, list)
        assert len(uiids) > 0, "Should have at least one UIID defined"

        # All UIIDs should be strings starting with flow_studio
        for uiid in uiids:
            assert isinstance(uiid, str)
            assert uiid.startswith("flow_studio"), f"UIID {uiid} doesn't start with flow_studio"

    def test_get_critique_schema_returns_valid_json_schema(self):
        """get_critique_schema returns a valid JSON schema dict."""
        from mcp_ux_spec import get_critique_schema

        schema = get_critique_schema()

        assert isinstance(schema, dict)
        # JSON Schema should have $schema and type
        assert "$schema" in schema or "type" in schema
        assert schema.get("type") == "object" or "properties" in schema


class TestMCPUXSpecIntegration:
    """Integration tests for MCP UX spec data consistency."""

    def test_layout_screens_match_manifest(self):
        """Layout screens in API match what's declared in manifest."""
        from mcp_ux_spec import get_layout_screens, get_ux_manifest

        manifest = get_ux_manifest()
        screens = get_layout_screens()

        # The manifest should reference the layout spec
        assert "layout_spec" in manifest

        # Number of screens should be consistent
        # (This is a loose check - actual implementation may vary)
        assert len(screens) > 0

    def test_uiids_in_screens_are_all_listed(self):
        """All UIIDs mentioned in screens are in the master UIID list."""
        from mcp_ux_spec import get_all_known_uiids, get_layout_screens

        all_uiids = set(get_all_known_uiids())
        screens = get_layout_screens()

        screen_uiids = set()
        for screen in screens:
            for region in screen.get("regions", []):
                for uiid in region.get("uiids", []):
                    screen_uiids.add(uiid)

        # All UIIDs in screens should be in the master list
        missing = screen_uiids - all_uiids
        assert not missing, f"UIIDs in screens but not in master list: {missing}"

    def test_critique_schema_is_valid_for_validation(self):
        """Critique schema can be used to validate JSON."""
        from mcp_ux_spec import get_critique_schema

        schema = get_critique_schema()

        # Schema should have the expected structure for validation
        assert "properties" in schema or "$defs" in schema

        # Schema properties should cover the expected critique fields
        props = schema.get("properties", {})
        if props:
            # Core required fields per ux_critique.schema.json
            expected_fields = {"screen_id", "timestamp", "issues"}
            defined_fields = set(props.keys())
            assert expected_fields.issubset(defined_fields), (
                f"Schema missing expected fields: {expected_fields - defined_fields}"
            )


class TestMCPUXSpecEdgeCases:
    """Edge case tests for MCP UX spec functions."""

    def test_get_layout_screen_by_id_with_empty_string(self):
        """get_layout_screen_by_id handles empty string gracefully."""
        from mcp_ux_spec import get_layout_screen_by_id

        result = get_layout_screen_by_id("")
        assert result is None

    def test_get_layout_screen_by_id_with_special_chars(self):
        """get_layout_screen_by_id handles special characters gracefully."""
        from mcp_ux_spec import get_layout_screen_by_id

        result = get_layout_screen_by_id("../../../etc/passwd")
        assert result is None

        result = get_layout_screen_by_id("<script>alert(1)</script>")
        assert result is None
