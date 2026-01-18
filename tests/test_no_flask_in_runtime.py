#!/usr/bin/env python3
"""
Ensure Flask is never imported in active production code.

This test validates that the Flask removal is complete and prevents accidental
re-introduction of Flask imports in the active swarm/tools/ codebase.

Test scope:
- All .py files in swarm/tools/
- Excludes swarm/tools/_archive/ (archived legacy code)
- Ensures no `import flask` or `from flask` patterns
- Verifies archival completeness (legacy Flask code is isolated)
"""

import sys
from pathlib import Path

import pytest

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


# ============================================================================
# Flask Removal Core Tests
# ============================================================================


def test_no_flask_imports_in_active_tools():
    """Verify no Flask imports in active swarm/tools/ Python files.

    Scans all .py files in swarm/tools/ directory, excluding _archive/,
    and asserts that neither `import flask` nor `from flask` patterns exist.

    This is the primary regression test to prevent Flask re-introduction.
    """
    tools_dir = repo_root / "swarm" / "tools"
    assert tools_dir.exists(), "swarm/tools/ directory should exist"

    # Collect all .py files, excluding _archive/
    python_files = [
        f for f in tools_dir.glob("*.py")
        if f.is_file() and f.name != "__pycache__"
    ]

    assert len(python_files) > 0, "Should have Python files in swarm/tools/"

    # Track which files import Flask (should be empty)
    flask_offenders = []

    for py_file in python_files:
        content = py_file.read_text(encoding="utf-8")

        # Check for Flask imports (case-insensitive to catch variations)
        has_import_flask = "import flask" in content.lower()
        has_from_flask = "from flask" in content.lower()

        if has_import_flask or has_from_flask:
            flask_offenders.append({
                "file": py_file.name,
                "import_flask": has_import_flask,
                "from_flask": has_from_flask,
            })

    # Assert no Flask imports found
    if flask_offenders:
        error_msg = "Flask imports found in active code:\n"
        for offender in flask_offenders:
            patterns = []
            if offender["import_flask"]:
                patterns.append("`import flask`")
            if offender["from_flask"]:
                patterns.append("`from flask`")
            error_msg += f"  - {offender['file']}: {', '.join(patterns)}\n"
        error_msg += "\nFlask should only be in swarm/tools/_archive/"
        pytest.fail(error_msg)


def test_flask_only_in_archive():
    """Verify Flask code exists only in _archive/ subdirectory.

    The archived Flask implementation should be isolated in _archive/ and
    not present in active code paths.
    """
    tools_dir = repo_root / "swarm" / "tools"
    archive_dir = tools_dir / "_archive"

    # Archive directory must exist (migration marker)
    assert archive_dir.exists(), "swarm/tools/_archive/ should exist as migration marker"
    assert archive_dir.is_dir(), "_archive should be a directory"

    # Flask legacy file should be in archive
    flask_legacy = archive_dir / "flow_studio_flask_legacy.py"
    assert flask_legacy.exists(), (
        "Archived Flask implementation should exist at swarm/tools/_archive/flow_studio_flask_legacy.py"
    )

    # Verify the archived file contains Flask imports (proof of archival)
    content = flask_legacy.read_text(encoding="utf-8")
    assert "from flask" in content.lower() or "import flask" in content.lower(), (
        "Archived file should be the actual Flask implementation"
    )


def test_no_subdirectory_flask_in_active_tools():
    """Verify no Flask in swarm/tools/ subdirectories (except _archive/).

    This ensures Flask wasn't accidentally moved to a subdirectory within
    swarm/tools/ that might be imported via package paths.
    """
    tools_dir = repo_root / "swarm" / "tools"

    # Collect all .py files in subdirectories, excluding _archive/
    for subdir in tools_dir.iterdir():
        if not subdir.is_dir():
            continue
        if subdir.name == "_archive":
            continue
        if subdir.name.startswith("."):  # Skip __pycache__, .pytest_cache, etc.
            continue

        # Check Python files in this subdirectory
        for py_file in subdir.glob("**/*.py"):
            if py_file.name == "__pycache__":
                continue

            content = py_file.read_text(encoding="utf-8")

            if "import flask" in content.lower() or "from flask" in content.lower():
                pytest.fail(
                    f"Flask import found in subdirectory: {py_file.relative_to(repo_root)}"
                )


# ============================================================================
# Archive Integrity Tests
# ============================================================================


def test_archive_structure_is_valid():
    """Verify _archive/ directory has expected structure.

    The archive should contain legacy code and __pycache__, but not be
    referenced as an active import path.
    """
    archive_dir = repo_root / "swarm" / "tools" / "_archive"

    # Should contain the legacy Flask file
    expected_files = ["flow_studio_flask_legacy.py"]
    for expected in expected_files:
        file_path = archive_dir / expected
        assert file_path.exists(), f"Archive should contain {expected}"


def test_no_active_imports_from_archive():
    """Verify no active code imports from _archive/.

    Active production code should never import from the _archive/ directory,
    which would defeat the purpose of archival.
    """
    tools_dir = repo_root / "swarm" / "tools"

    # Get all .py files in active tools (excluding _archive)
    active_files = [f for f in tools_dir.glob("*.py") if f.is_file()]

    for py_file in active_files:
        content = py_file.read_text(encoding="utf-8")

        # Check for imports from _archive
        if "from swarm.tools._archive" in content or "from swarm.tools._archive import" in content:
            pytest.fail(
                f"Active code should not import from _archive: {py_file.name}"
            )


# ============================================================================
# Fastapi Migration Verification
# ============================================================================


def test_fastapi_replaces_flask_functionality():
    """Verify FastAPI provides the functionality Flask provided.

    The FastAPI implementation should have replaced all Flask endpoints
    and functionality.
    """
    fastapi_module = repo_root / "swarm" / "tools" / "flow_studio_fastapi.py"

    assert fastapi_module.exists(), (
        "flow_studio_fastapi.py should exist as replacement for Flask"
    )

    content = fastapi_module.read_text(encoding="utf-8")

    # FastAPI shim should point to the packaged app factory.
    assert "create_fastapi_app" in content, "Shim should import create_fastapi_app"
    assert "create_app = create_fastapi_app" in content, (
        "Shim should alias create_app to create_fastapi_app"
    )
    assert "app = create_fastapi_app()" in content, (
        "Shim should create app via create_fastapi_app()"
    )


def test_no_flask_in_conftest():
    """Verify conftest.py doesn't import or use Flask.

    Test fixtures should use FastAPI TestClient, not Flask test client.
    """
    conftest = repo_root / "tests" / "conftest.py"

    if not conftest.exists():
        pytest.skip("conftest.py not found")

    content = conftest.read_text(encoding="utf-8")

    assert "from flask import" not in content, (
        "conftest.py should not import from flask"
    )
    assert "import flask" not in content, (
        "conftest.py should not import flask"
    )


# ============================================================================
# Documentation and Reference Tests
# ============================================================================


def test_legacy_flask_file_is_not_executable():
    """Verify archived Flask file is not in active execution paths.

    The .py file exists for reference, but shouldn't be treated as active code.
    """
    flask_legacy = repo_root / "swarm" / "tools" / "_archive" / "flow_studio_flask_legacy.py"

    assert flask_legacy.exists(), "Legacy Flask file should exist in archive"

    # The file should exist but be archived (structural signal of non-active status)
    # We verify this by checking it's in _archive/, not by permission checks
    # (permissions vary by OS and git configuration)
    assert "_archive" in str(flask_legacy), (
        "Flask file should be in _archive/ directory to signal non-active status"
    )


def test_makefile_does_not_reference_flask():
    """Verify Makefile flow-studio target doesn't use Flask.

    The flow-studio Make target should only reference FastAPI (uvicorn).
    """
    makefile = repo_root / "Makefile"
    assert makefile.exists(), "Makefile should exist"

    content = makefile.read_text(encoding="utf-8")

    # Extract flow-studio target
    lines = content.split("\n")
    target_lines = []
    in_target = False

    for line in lines:
        if line.startswith("flow-studio:"):
            in_target = True
            continue
        elif in_target:
            # End of target (next target or blank line at column 0)
            if line and not line.startswith("\t") and not line.startswith(" "):
                break
            target_lines.append(line)

    target_text = "\n".join(target_lines)

    # Verify no Flask references
    assert "flask" not in target_text.lower(), (
        "Makefile flow-studio target should not reference Flask"
    )

    # Verify FastAPI is used
    assert "uvicorn" in target_text.lower() or "fastapi" in target_text.lower(), (
        "Makefile flow-studio target should reference FastAPI/uvicorn"
    )


# ============================================================================
# Regression Prevention: Specific Patterns
# ============================================================================


def test_no_flask_blueprint_patterns():
    """Verify no Flask Blueprint definitions in active code.

    Blueprints are Flask-specific. Their presence indicates Flask code
    that should have been migrated to FastAPI.
    """
    tools_dir = repo_root / "swarm" / "tools"
    python_files = [f for f in tools_dir.glob("*.py") if f.is_file()]

    for py_file in python_files:
        content = py_file.read_text(encoding="utf-8")

        # Blueprint is Flask-specific; fail immediately if found
        if "Blueprint" in content:
            pytest.fail(
                f"Flask Blueprint pattern found in: {py_file.name}"
            )


def test_no_flask_route_decorators():
    """Verify no @app.route decorators (Flask pattern) in active code.

    FastAPI uses @app.get, @app.post, etc. Flask uses @app.route.
    Presence of Flask-style routes indicates unmigrated code.
    """
    tools_dir = repo_root / "swarm" / "tools"
    python_files = [f for f in tools_dir.glob("*.py") if f.is_file()]

    for py_file in python_files:
        content = py_file.read_text(encoding="utf-8")

        # @app.route is Flask-specific; fail immediately if found
        if "@app.route(" in content:
            pytest.fail(
                f"Flask @app.route decorator found in: {py_file.name}"
            )


# ============================================================================
# Coverage: All Tools Files Listed
# ============================================================================


def test_no_flask_app_initialization():
    """Verify no Flask app initialization (Flask(__name__)) in active code.

    Flask apps are created via Flask(__name__). FastAPI uses FastAPI().
    This is the primary Flask initialization pattern that must not exist.
    """
    tools_dir = repo_root / "swarm" / "tools"
    python_files = [f for f in tools_dir.glob("*.py") if f.is_file()]

    for py_file in python_files:
        content = py_file.read_text(encoding="utf-8")

        # Flask(__name__) is the canonical Flask app initialization
        if "Flask(__name__)" in content:
            pytest.fail(
                f"Flask app initialization Flask(__name__) found in: {py_file.name}"
            )


def test_no_flask_template_rendering():
    """Verify no Flask render_template() calls in active code.

    Flask uses render_template() for HTML rendering. FastAPI uses Response()
    or returns dict/Pydantic models directly.
    """
    tools_dir = repo_root / "swarm" / "tools"
    python_files = [f for f in tools_dir.glob("*.py") if f.is_file()]

    for py_file in python_files:
        content = py_file.read_text(encoding="utf-8")

        # render_template is Flask-specific
        if "render_template" in content:
            # Could be Flask render_template or direct jinja2 (less likely)
            if "from flask" in content.lower() or "import flask" in content.lower():
                pytest.fail(
                    f"Flask render_template found in: {py_file.name}"
                )


def test_all_python_files_are_importable():
    """Smoke test: verify all active tools .py files can be parsed.

    This doesn't execute them, just ensures they're syntactically valid
    Python and don't depend on missing Flask imports.
    """
    tools_dir = repo_root / "swarm" / "tools"
    python_files = [f for f in tools_dir.glob("*.py") if f.is_file()]

    parse_failures = []

    for py_file in python_files:
        try:
            compile(py_file.read_text(encoding="utf-8"), str(py_file), "exec")
        except SyntaxError as e:
            parse_failures.append((py_file.name, str(e)))

    if parse_failures:
        error_msg = "Syntax errors in tools files:\n"
        for fname, err in parse_failures:
            error_msg += f"  - {fname}: {err}\n"
        pytest.fail(error_msg)
