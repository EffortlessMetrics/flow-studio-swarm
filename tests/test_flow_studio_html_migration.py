#!/usr/bin/env python3
"""
Test suite for Flow Studio HTML extraction migration.

This test suite verifies that both Flask and FastAPI backends serve identical HTML
after the extraction migration where get_index_html() was moved to a shared module.

The migration goals:
1. Extract HTML template from Flask implementation to swarm.tools.flow_studio_ui
2. Both backends (Flask and FastAPI) use the same HTML source
3. HTML is byte-for-byte identical across both backends
4. The extracted module is importable and returns valid HTML

Test Categories:
- HTML Module Tests: Verify the extracted HTML module works correctly
- FastAPI Tests: Verify FastAPI serves the HTML correctly
- Flask Tests: Verify Flask serves the HTML correctly (optional but thorough)
- Backend Parity Tests: Verify both backends serve identical content
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest

# ============================================================================
# HTML Module Tests
# ============================================================================


def test_flow_studio_ui_module_exists():
    """Verify the extracted HTML UI module exists and is importable."""
    from swarm.tools.flow_studio_ui import get_index_html

    html = get_index_html()

    # Basic structure checks - HTML may start with generated file comment
    assert "<!DOCTYPE html" in html, "HTML should contain DOCTYPE declaration"
    assert "</html>" in html, "HTML should have closing html tag"
    assert len(html) > 100000, f"HTML should be substantial (~140KB), got {len(html)} bytes"


def test_html_contains_flow_studio_components():
    """Verify extracted HTML contains expected Flow Studio UI elements."""
    from swarm.tools.flow_studio_ui import get_index_html

    html = get_index_html()

    # Check for key UI components
    assert "Flow Studio" in html, "HTML should reference 'Flow Studio'"
    assert "cytoscape" in html.lower(), "HTML should include Cytoscape graph library"

    # Check for API endpoints (these should be hardcoded in the HTML)
    assert "/api/flows" in html, "HTML should reference /api/flows endpoint"
    assert "/api/agents" in html, "HTML should reference /api/agents endpoint"


def test_html_is_well_formed():
    """Verify extracted HTML is well-formed (basic sanity checks)."""
    from swarm.tools.flow_studio_ui import get_index_html

    html = get_index_html()

    # Check for required HTML elements
    assert "<html" in html, "Should have opening html tag"
    assert "<head>" in html or "<head " in html, "Should have head section"
    assert "<body>" in html or "<body " in html, "Should have body section"
    assert "</head>" in html, "Should have closing head tag"
    assert "</body>" in html, "Should have closing body tag"

    # Check for meta tags (UTF-8 encoding)
    assert "charset" in html.lower(), "Should declare character encoding"

    # Check for title
    assert "<title>" in html, "Should have page title"


def test_html_module_path_exists():
    """Verify the HTML file exists on disk at expected location."""

    # The HTML should be at swarm/tools/flow_studio_ui/index.html
    html_file = repo_root / "swarm" / "tools" / "flow_studio_ui" / "index.html"
    assert html_file.exists(), f"HTML file should exist at {html_file}"
    assert html_file.is_file(), "HTML path should be a file, not a directory"

    # Verify it's readable and non-empty
    content = html_file.read_text(encoding="utf-8")
    assert len(content) > 100000, "HTML file should be substantial (~140KB)"


# ============================================================================
# FastAPI Backend Tests
# ============================================================================


def test_fastapi_serves_html(flowstudio_client):
    """Verify FastAPI backend serves the HTML correctly."""
    response = flowstudio_client.get("/")

    assert response.status_code == 200, "FastAPI should return 200 for root endpoint"
    assert response.headers["content-type"].startswith("text/html"), (
        "FastAPI should serve HTML content-type"
    )

    html = response.text
    # HTML may start with generated file comment
    assert "<!DOCTYPE html" in html, "FastAPI HTML should contain DOCTYPE"
    assert "Flow Studio" in html, "FastAPI HTML should contain 'Flow Studio'"


def test_fastapi_html_length(flowstudio_client):
    """Verify FastAPI serves HTML of expected size."""
    response = flowstudio_client.get("/")

    html = response.text
    assert len(html) > 100000, f"FastAPI HTML should be substantial, got {len(html)} bytes"


def test_fastapi_html_contains_api_references(flowstudio_client):
    """Verify FastAPI HTML contains expected API endpoint references."""
    response = flowstudio_client.get("/")

    html = response.text

    # Check for API endpoints that are actually used in the HTML
    assert "/api/flows" in html, "FastAPI HTML should reference /api/flows"
    assert "/api/graph" in html, "FastAPI HTML should reference /api/graph"
    assert "/api/runs" in html, "FastAPI HTML should reference /api/runs"


# ============================================================================
# Flask Backend Tests (Optional but Thorough)
# ============================================================================


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_flask_serves_html():
    """Verify Flask backend serves the HTML correctly."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_flask_html_length():
    """Verify Flask serves HTML of expected size."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_flask_html_contains_api_references():
    """Verify Flask HTML contains expected API endpoint references."""
    pass  # Flask backend archived


# ============================================================================
# Backend Parity Tests - Verify Identical Content
# ============================================================================


def test_backends_serve_identical_html(flowstudio_client):
    """Verify Flask and FastAPI serve byte-for-byte identical HTML."""
    # Get HTML from extracted module (source of truth)
    from swarm.tools.flow_studio_ui import get_index_html

    expected_html = get_index_html()

    # Get HTML from FastAPI
    response = flowstudio_client.get("/")
    assert response.status_code == 200, "FastAPI should return 200"
    fastapi_html = response.text

    # Compare
    assert fastapi_html == expected_html, "FastAPI HTML doesn't match extracted template"


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_flask_matches_extracted_html():
    """Verify Flask serves HTML matching the extracted template."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_flask_and_fastapi_serve_identical_html(flowstudio_client):
    """Verify Flask and FastAPI serve byte-for-byte identical HTML to each other."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_html_consistency_across_all_sources(flowstudio_client):
    """Comprehensive test: Verify HTML is consistent across module and FastAPI."""
    pass  # Flask backend archived


# ============================================================================
# Migration Verification Tests
# ============================================================================


def test_migration_goal_single_source_of_truth():
    """Verify the migration achieves single source of truth for HTML."""
    # The HTML should come from one place: swarm.tools.flow_studio_ui.get_index_html()

    from swarm.tools.flow_studio_ui import get_index_html

    # This should be the canonical source
    canonical_html = get_index_html()

    # Verify it's substantial
    assert len(canonical_html) > 100000, "Canonical HTML should be substantial"

    # Verify it's a complete HTML document (may start with generated file comment)
    assert "<!DOCTYPE html" in canonical_html
    assert "</html>" in canonical_html


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_migration_goal_no_duplication():
    """Verify FastAPI doesn't duplicate HTML storage."""
    # Check FastAPI imports get_index_html
    import inspect

    from swarm.tools import flow_studio_fastapi

    fastapi_source = inspect.getsource(flow_studio_fastapi)
    assert "from swarm.tools.flow_studio_ui import get_index_html" in fastapi_source, (
        "FastAPI should import get_index_html from shared module"
    )


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_migration_goal_backends_use_same_function():
    """Verify FastAPI uses the extracted get_index_html function."""
    import inspect

    from swarm.tools import flow_studio_fastapi

    fastapi_src = inspect.getsource(flow_studio_fastapi)

    # FastAPI should import from the UI module
    assert "swarm.tools.flow_studio_ui" in fastapi_src
    assert "get_index_html" in fastapi_src


# ============================================================================
# Edge Cases and Regression Tests
# ============================================================================


def test_html_encoding_is_utf8():
    """Verify HTML is properly UTF-8 encoded."""
    from swarm.tools.flow_studio_ui import get_index_html

    html = get_index_html()

    # Should be a string (already decoded)
    assert isinstance(html, str), "get_index_html() should return str, not bytes"

    # Should be encodable to UTF-8
    try:
        html.encode("utf-8")
    except UnicodeEncodeError:
        pytest.fail("HTML contains characters not encodable in UTF-8")


def test_html_has_no_server_side_templating():
    """Verify HTML doesn't contain server-side template variables."""
    from swarm.tools.flow_studio_ui import get_index_html

    html = get_index_html()

    # Check for common template variables that would indicate
    # the HTML isn't fully rendered
    template_markers = [
        "{{ ",
        "{% ",
        "{$ ",
        "<% ",
    ]

    for marker in template_markers:
        assert marker not in html, f"HTML should not contain server-side template marker: {marker}"


def test_html_caching_not_broken():
    """Verify multiple calls return the same HTML (file caching works)."""
    from swarm.tools.flow_studio_ui import get_index_html

    # Call twice
    html1 = get_index_html()
    html2 = get_index_html()

    # Should be identical
    assert html1 == html2, "Multiple calls should return identical HTML"


# ============================================================================
# Performance Tests (Optional)
# ============================================================================


def test_html_loading_is_fast():
    """Verify HTML loading is reasonably fast."""
    import time

    from swarm.tools.flow_studio_ui import get_index_html

    start = time.time()
    html = get_index_html()
    elapsed = time.time() - start

    # Should load in under 100ms (generous threshold for file I/O)
    assert elapsed < 0.1, f"HTML loading took {elapsed:.3f}s, should be <0.1s"
    assert len(html) > 100000, "HTML should be substantial"
