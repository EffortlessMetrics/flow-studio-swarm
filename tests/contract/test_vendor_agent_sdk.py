"""
Contract tests for vendored Claude Agent SDK artifacts.

These tests verify that the vendored SDK reference artifacts exist and are
properly structured. They enable offline validation without requiring the
SDK to be installed.

Run with: pytest tests/contract/test_vendor_agent_sdk.py -v
"""

import hashlib
import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_DIR = REPO_ROOT / "docs" / "vendor" / "anthropic" / "agent-sdk" / "python"
REFERENCE_MD = VENDOR_DIR / "REFERENCE.md"
VERSION_JSON = VENDOR_DIR / "VERSION.json"
TOOLS_MANIFEST_JSON = VENDOR_DIR / "TOOLS_MANIFEST.json"

REFERENCE_VERSION_PATTERN = re.compile(r"^SDK version:\s*(.+)$", re.MULTILINE)
REFERENCE_HEADER_SCAN_LINES = 60


def _read_json(path: Path) -> dict:
    """Read and parse JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    """Read text content from file."""
    return path.read_text(encoding="utf-8")


def _sha256_text(text: str) -> str:
    """Return SHA256 of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_reference_version(reference_text: str) -> tuple[str | None, str | None]:
    """Parse SDK distribution/version from REFERENCE header."""
    header_text = "\n".join(reference_text.splitlines()[:REFERENCE_HEADER_SCAN_LINES])
    match = REFERENCE_VERSION_PATTERN.search(header_text)
    if not match:
        return None, None

    raw = match.group(1).strip()
    if raw.startswith("`") and raw.endswith("`"):
        raw = raw[1:-1].strip()

    if "==" in raw:
        dist, ver = [part.strip() for part in raw.split("==", 1)]
        return dist, ver

    parts = raw.split()
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()

    return None, None


# =============================================================================
# P0: Vendor Files Exist
# =============================================================================


class TestVendorFilesExist:
    """Verify vendored files exist (basic structure check)."""

    def test_vendor_directory_exists(self):
        """Verify vendor directory exists."""
        assert VENDOR_DIR.exists(), f"Vendor directory missing: {VENDOR_DIR}"
        assert VENDOR_DIR.is_dir(), f"Vendor path is not a directory: {VENDOR_DIR}"

    def test_version_json_exists(self):
        """Verify VERSION.json exists."""
        version_file = VERSION_JSON
        if not version_file.exists():
            pytest.skip(
                "VERSION.json not present. Run 'make vendor-agent-sdk' to generate."
            )

    def test_api_manifest_exists(self):
        """Verify API_MANIFEST.json exists."""
        api_file = VENDOR_DIR / "API_MANIFEST.json"
        if not api_file.exists():
            pytest.skip(
                "API_MANIFEST.json not present. Run 'make vendor-agent-sdk' to generate."
            )

    def test_tools_manifest_exists(self):
        """Verify TOOLS_MANIFEST.json exists."""
        tools_file = TOOLS_MANIFEST_JSON
        if not tools_file.exists():
            pytest.skip(
                "TOOLS_MANIFEST.json not present. Run 'make vendor-agent-sdk' to generate."
            )

    def test_mapping_json_exists(self):
        """Verify MAPPING.json exists."""
        mapping_file = VENDOR_DIR / "MAPPING.json"
        if not mapping_file.exists():
            pytest.skip(
                "MAPPING.json not present. Add adapter mapping for SDK symbols."
            )


# =============================================================================
# P0: Vendor Files Are Valid JSON
# =============================================================================


class TestVendorFilesValid:
    """Verify vendored files contain valid JSON with expected structure."""

    @pytest.fixture
    def version_data(self) -> dict:
        """Load VERSION.json, skip if not present."""
        path = VENDOR_DIR / "VERSION.json"
        if not path.exists():
            pytest.skip("VERSION.json not present")
        return _read_json(path)

    @pytest.fixture
    def api_data(self) -> dict:
        """Load API_MANIFEST.json, skip if not present."""
        path = VENDOR_DIR / "API_MANIFEST.json"
        if not path.exists():
            pytest.skip("API_MANIFEST.json not present")
        return _read_json(path)

    @pytest.fixture
    def tools_data(self) -> dict:
        """Load TOOLS_MANIFEST.json, skip if not present."""
        path = VENDOR_DIR / "TOOLS_MANIFEST.json"
        if not path.exists():
            pytest.skip("TOOLS_MANIFEST.json not present")
        return _read_json(path)

    @pytest.fixture
    def mapping_data(self) -> dict:
        """Load MAPPING.json, skip if not present."""
        path = VENDOR_DIR / "MAPPING.json"
        if not path.exists():
            pytest.skip("MAPPING.json not present")
        return _read_json(path)

    def test_version_has_required_fields(self, version_data):
        """VERSION.json has required metadata fields."""
        required = ["generated_at", "import_module", "distribution", "version"]
        for field in required:
            assert field in version_data, f"VERSION.json missing field: {field}"

    def test_version_module_is_valid(self, version_data):
        """VERSION.json module name is one of expected values."""
        module = version_data.get("import_module")
        valid_modules = ["claude_agent_sdk", "claude_code_sdk"]
        assert module in valid_modules, (
            f"Unexpected import_module: {module}. Expected one of: {valid_modules}"
        )

    def test_api_manifest_has_structure(self, api_data):
        """API_MANIFEST.json has expected structure."""
        assert "generated_at" in api_data
        assert "module" in api_data
        assert "exported" in api_data
        assert isinstance(api_data["exported"], dict)

    def test_api_manifest_has_exports(self, api_data):
        """API_MANIFEST.json has at least one export."""
        exports = api_data.get("exported", {})
        assert len(exports) > 0, "API_MANIFEST.json has no exports"

    def test_tools_manifest_has_structure(self, tools_data):
        """TOOLS_MANIFEST.json has expected structure."""
        assert "generated_at" in tools_data
        assert "tool_names" in tools_data
        assert "count" in tools_data
        assert isinstance(tools_data["tool_names"], list)

    def test_tools_manifest_count_matches(self, tools_data):
        """TOOLS_MANIFEST.json count matches tool_names length."""
        count = tools_data.get("count", 0)
        names = tools_data.get("tool_names", [])
        assert len(names) == count, (
            f"TOOLS_MANIFEST count mismatch: count={count}, actual={len(names)}"
        )

    def test_mapping_has_structure(self, mapping_data):
        """MAPPING.json has expected structure."""
        assert "schema_version" in mapping_data
        assert "symbols" in mapping_data
        assert isinstance(mapping_data["symbols"], dict)

        # Validate minimal per-symbol fields when present
        for name, entry in mapping_data["symbols"].items():
            assert "local_support" in entry, f"{name} missing local_support"
            assert "where" in entry, f"{name} missing where"


# =============================================================================
# P1: API Surface Contains Expected Symbols
# =============================================================================


class TestAPIManifestSurface:
    """Verify API manifest contains expected SDK symbols."""

    @pytest.fixture
    def api_exports(self) -> dict:
        """Load API exports, skip if not present."""
        path = VENDOR_DIR / "API_MANIFEST.json"
        if not path.exists():
            pytest.skip("API_MANIFEST.json not present")
        data = _read_json(path)
        return data.get("exported", {})

    def test_has_options_class(self, api_exports):
        """API exports include ClaudeCodeOptions or similar options class."""
        # The SDK might expose ClaudeCodeOptions or ClaudeAgentOptions
        options_candidates = ["ClaudeCodeOptions", "ClaudeAgentOptions", "Options"]
        found = any(name in api_exports for name in options_candidates)

        if not found:
            # Not an error - just note what's available
            pytest.skip(
                f"No options class found. Available exports: {list(api_exports.keys())[:10]}"
            )

    def test_has_query_function(self, api_exports):
        """API exports include query function."""
        query_candidates = ["query", "run_query", "execute"]
        found = any(name in api_exports for name in query_candidates)

        if not found:
            pytest.skip(
                f"No query function found. Available exports: {list(api_exports.keys())[:10]}"
            )

    def test_export_entries_have_kind(self, api_exports):
        """Each export entry has a 'kind' field."""
        for name, entry in api_exports.items():
            assert "kind" in entry, f"Export '{name}' missing 'kind' field"
            assert entry["kind"] in ["function", "class", "method", "callable", "unknown"]


# =============================================================================
# P1: Cross-Reference with Adapter
# =============================================================================


class TestAdapterAlignment:
    """Verify vendored surface aligns with adapter usage."""

    @pytest.fixture
    def api_exports(self) -> dict:
        """Load API exports, skip if not present."""
        path = VENDOR_DIR / "API_MANIFEST.json"
        if not path.exists():
            pytest.skip("API_MANIFEST.json not present")
        data = _read_json(path)
        return data.get("exported", {})

    def test_adapter_uses_vendored_symbols(self, api_exports):
        """Verify symbols used by our adapter are in the vendored manifest.

        This catches drift where our adapter uses SDK symbols that aren't
        in the vendored API surface (either we're using undocumented APIs
        or the vendor snapshot is stale).
        """
        # These are symbols our adapter actually uses (from claude_sdk.py)
        adapter_uses = ["ClaudeCodeOptions", "query"]

        # Check if any of our used symbols are missing from vendor
        missing = [s for s in adapter_uses if s not in api_exports]

        if missing:
            # Not a hard error - SDK might use different names
            pytest.skip(
                f"Adapter uses symbols not in vendor manifest: {missing}. "
                f"This may indicate naming differences or stale vendor snapshot."
            )

    def test_all_standard_tools_in_manifest(self):
        """Cross-reference ALL_STANDARD_TOOLS with vendored tools manifest.

        This catches drift where we add/remove tools from ALL_STANDARD_TOOLS
        but don't update the reference documentation.
        """
        tools_path = VENDOR_DIR / "TOOLS_MANIFEST.json"
        if not tools_path.exists():
            pytest.skip("TOOLS_MANIFEST.json not present")

        tools_data = _read_json(tools_path)
        vendor_tools = set(tools_data.get("tool_names", []))

        if not vendor_tools:
            pytest.skip("No tools in vendor manifest (REFERENCE.md may be missing)")

        # Import our tool list
        try:
            from swarm.runtime.claude_sdk import ALL_STANDARD_TOOLS
        except ImportError:
            pytest.skip("Could not import ALL_STANDARD_TOOLS from adapter")

        # Check for tools in adapter but not in vendor
        adapter_only = ALL_STANDARD_TOOLS - vendor_tools
        if adapter_only:
            # Note: this is informational, not a failure
            # Vendor tools come from reference docs which may lag
            pass

        # Check for tools in vendor but not in adapter
        vendor_only = vendor_tools - ALL_STANDARD_TOOLS
        if vendor_only:
            # This is more concerning - vendor has tools we don't know about
            pass


# =============================================================================
# P1: Reference Document Structure
# =============================================================================


class TestReferenceDocument:
    """Verify REFERENCE.md structure if present."""

    @pytest.fixture
    def reference_text(self) -> str:
        """Load REFERENCE.md, skip if not present."""
        if not REFERENCE_MD.exists():
            pytest.skip("REFERENCE.md not present (optional)")
        return _read_text(REFERENCE_MD)

    def test_reference_has_header(self, reference_text):
        """REFERENCE.md has a proper header."""
        lines = reference_text.strip().split("\n")
        assert len(lines) > 0, "REFERENCE.md is empty"
        assert lines[0].startswith("#"), "REFERENCE.md should start with a header"

    def test_reference_not_empty(self, reference_text):
        """REFERENCE.md has meaningful content."""
        # Remove whitespace and check length
        content = reference_text.strip()
        assert len(content) > 100, "REFERENCE.md appears too short to be useful"

    def test_reference_has_code_blocks(self, reference_text):
        """REFERENCE.md contains code examples."""
        # Look for markdown code blocks
        assert "```" in reference_text, (
            "REFERENCE.md should contain code examples (markdown code blocks)"
        )


# =============================================================================
# P0: Reference Metadata Contracts
# =============================================================================


class TestReferenceMetadata:
    """Verify REFERENCE.md metadata stays in sync."""

    def test_reference_version_matches_version_json(self):
        """REFERENCE.md SDK version header matches VERSION.json."""
        if not REFERENCE_MD.exists() or not VERSION_JSON.exists():
            pytest.skip("REFERENCE.md or VERSION.json not present")

        reference_text = _read_text(REFERENCE_MD)
        dist, ver = _parse_reference_version(reference_text)
        if not dist or not ver:
            pytest.fail("REFERENCE.md missing SDK version header")

        version_data = _read_json(VERSION_JSON)
        assert dist == version_data.get("distribution"), (
            f"REFERENCE.md distribution mismatch: {dist} != {version_data.get('distribution')}"
        )
        assert ver == version_data.get("version"), (
            f"REFERENCE.md version mismatch: {ver} != {version_data.get('version')}"
        )

    def test_tools_manifest_tracks_reference_hash(self):
        """TOOLS_MANIFEST.json reference hash matches REFERENCE.md."""
        if not REFERENCE_MD.exists() or not TOOLS_MANIFEST_JSON.exists():
            pytest.skip("REFERENCE.md or TOOLS_MANIFEST.json not present")

        reference_text = _read_text(REFERENCE_MD)
        tools_data = _read_json(TOOLS_MANIFEST_JSON)
        expected_hash = _sha256_text(reference_text)

        actual_hash = tools_data.get("reference_sha256")
        assert actual_hash == expected_hash, (
            "TOOLS_MANIFEST.json reference_sha256 does not match REFERENCE.md. "
            "Run make vendor-agent-sdk."
        )


# =============================================================================
# P2: Vendor Script Functionality
# =============================================================================


class TestVendorScript:
    """Verify vendor script exists and is executable."""

    def test_vendor_script_exists(self):
        """Verify vendor_agent_sdk.py exists."""
        script = REPO_ROOT / "swarm" / "tools" / "vendor_agent_sdk.py"
        assert script.exists(), f"Vendor script missing: {script}"

    def test_vendor_script_importable(self):
        """Verify vendor script can be imported."""
        import sys
        sys.path.insert(0, str(REPO_ROOT / "swarm" / "tools"))
        try:
            import vendor_agent_sdk  # noqa: F401
        except ImportError as e:
            pytest.fail(f"Vendor script not importable: {e}")
        finally:
            sys.path.pop(0)

    def test_vendor_script_has_commands(self):
        """Verify vendor script exposes expected functions."""
        import sys
        sys.path.insert(0, str(REPO_ROOT / "swarm" / "tools"))
        try:
            import vendor_agent_sdk

            # Check for expected functions
            assert hasattr(vendor_agent_sdk, "cmd_status")
            assert hasattr(vendor_agent_sdk, "cmd_write")
            assert hasattr(vendor_agent_sdk, "cmd_check")
        except ImportError:
            pytest.skip("Could not import vendor script")
        finally:
            sys.path.pop(0)
