#!/usr/bin/env python3
"""
Tests for Flow Studio UI ID integration (part 2).

Additional integration tests split from test_flow_studio_ui_ids_integration.py
to meet complexity requirements.
"""

from pathlib import Path
import re
import pytest
from tests.flow_studio_ui_ids_helpers import extract_uiids_from_html, get_flow_studio_html

# Add repo root to path so swarm imports work
import sys
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


class TestDynamicUIIDs:
    """Tests for data-uiid attributes in dynamically rendered components."""

    def test_backend_badge_uiid_in_run_history(self):
        """Verify backend badge UIID pattern is in run_history.ts."""
        js_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "js" / "run_history.js"
        assert js_file.exists(), "run_history.js should exist"

        content = js_file.read_text(encoding="utf-8")

        # Should contain the backend badge UIID pattern
        assert "flow_studio.sidebar.run_history.item.badge.backend:" in content, (
            "run_history.js should render backend badges with data-uiid"
        )

    def test_events_toggle_uiid_in_run_detail_modal(self):
        """Verify events toggle UIID is in run_detail_modal.ts."""
        js_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "js" / "run_detail_modal.js"
        assert js_file.exists(), "run_detail_modal.js should exist"

        content = js_file.read_text(encoding="utf-8")

        # Should contain the events toggle UIID
        assert "flow_studio.modal.run_detail.events.toggle" in content, (
            "run_detail_modal.js should render events toggle with data-uiid"
        )

    def test_events_container_uiid_in_run_detail_modal(self):
        """Verify events container UIID is in run_detail_modal.ts."""
        js_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "js" / "run_detail_modal.js"
        assert js_file.exists(), "run_detail_modal.js should exist"

        content = js_file.read_text(encoding="utf-8")

        # Should contain the events container UIID
        assert "flow_studio.modal.run_detail.events.container" in content, (
            "run_detail_modal.js should render events container with data-uiid"
        )

    def test_exemplar_checkbox_uiid_in_run_detail_modal(self):
        """Verify exemplar checkbox UIID is in run_detail_modal.ts."""
        js_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "js" / "run_detail_modal.js"
        assert js_file.exists(), "run_detail_modal.js should exist"

        content = js_file.read_text(encoding="utf-8")

        # Should contain the exemplar checkbox UIID
        assert "flow_studio.modal.run_detail.exemplar" in content, (
            "run_detail_modal.js should render exemplar checkbox with data-uiid"
        )

    def test_rerun_button_uiid_in_run_detail_modal(self):
        """Verify re-run button UIID is in run_detail_modal.ts."""
        js_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "js" / "run_detail_modal.js"
        assert js_file.exists(), "run_detail_modal.js should exist"

        content = js_file.read_text(encoding="utf-8")

        # Should contain the re-run button UIID
        assert "flow_studio.modal.run_detail.rerun" in content, (
            "run_detail_modal.js should render re-run button with data-uiid"
        )


class TestBackendBadgeUIIDs:
    """Tests for backend badge data-uiid attributes."""

    def test_backend_badge_pattern_documented(self):
        """Document backend badge UIID pattern for automation."""
        ts_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "src" / "domain.ts"
        content = ts_file.read_text(encoding="utf-8")

        # The type should include run detail modal UIIDs
        assert "flow_studio.modal.run_detail" in content, (
            "domain.ts FlowStudioUIID should include run_detail modal UIIDs"
        )


class TestEventsTimelineUIIDs:
    """Tests for events timeline data-uiid attributes."""

    def test_events_uiids_defined_in_domain(self):
        """Verify events UIIDs are defined in domain.ts FlowStudioUIID type."""
        ts_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "src" / "domain.ts"
        content = ts_file.read_text(encoding="utf-8")

        # Should include events toggle and container UIIDs
        assert "flow_studio.modal.run_detail.events.toggle" in content, (
            "domain.ts should define events.toggle UIID"
        )
        assert "flow_studio.modal.run_detail.events.container" in content, (
            "domain.ts should define events.container UIID"
        )


class TestUIReadyHandshake:
    """Tests for UI ready state handshake (data-ui-ready attribute)."""

    def test_ui_ready_states_documented_in_js(self):
        """Verify the JS code documents all three UI ready states."""
        js_file = (
            repo_root
            / "swarm"
            / "tools"
            / "flow_studio_ui"
            / "js"
            / "flow-studio-app.js"
        )
        js_content = js_file.read_text(encoding="utf-8")

        # All three states should be documented
        assert 'uiReady = "loading"' in js_content, "Should have loading state"
        assert 'uiReady = "ready"' in js_content, "Should have ready state"
        assert 'uiReady = "error"' in js_content, "Should have error state"

    def test_ui_ready_handshake_example(self):
        """Demonstrate the UI ready handshake pattern for tests/agents."""
        pass
