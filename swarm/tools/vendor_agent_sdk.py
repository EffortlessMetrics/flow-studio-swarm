#!/usr/bin/env python3
"""
Vendoring + drift checking for Claude Agent SDK (Python) reference.

This script vendors a machine-checkable snapshot of the Claude Agent SDK API surface.
It enables Flow Studio agents and reviewers to work offline while maintaining
the ability to detect drift between vendored docs and the installed SDK.

Outputs (checked-in):
- docs/vendor/anthropic/agent-sdk/python/VERSION.json     (generated; SDK metadata)
- docs/vendor/anthropic/agent-sdk/python/API_MANIFEST.json (generated; API surface)
- docs/vendor/anthropic/agent-sdk/python/TOOLS_MANIFEST.json (generated; tool names from REFERENCE)

Usage:
  uv run python swarm/tools/vendor_agent_sdk.py --write
  uv run python swarm/tools/vendor_agent_sdk.py --check
  uv run python swarm/tools/vendor_agent_sdk.py --check --strict
  uv run python swarm/tools/vendor_agent_sdk.py --status

Design:
  - SDK imports centralized: tries claude_agent_sdk first, falls back to claude_code_sdk
  - API manifest: introspects installed package for public symbols
  - Tools manifest: extracts tool names from REFERENCE.md (if present)
  - Check mode: verifies committed artifacts match installed SDK
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import inspect
import json
import os
import re
import sys
from datetime import datetime, timezone
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version as dist_version
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_DIR = REPO_ROOT / "docs" / "vendor" / "anthropic" / "agent-sdk" / "python"
REFERENCE_MD = VENDOR_DIR / "REFERENCE.md"
VERSION_JSON = VENDOR_DIR / "VERSION.json"
API_MANIFEST_JSON = VENDOR_DIR / "API_MANIFEST.json"
TOOLS_MANIFEST_JSON = VENDOR_DIR / "TOOLS_MANIFEST.json"

# Import candidates: official first, legacy fallback
IMPORT_CANDIDATES: List[Tuple[str, str]] = [
    ("claude_agent_sdk", "claude-agent-sdk"),  # module name, dist name
    ("claude_code_sdk", "claude-code-sdk"),    # legacy fallback
]

# Tool name extraction patterns from reference docs
# Primary: "**Tool name:** `X`" pattern
TOOL_NAME_PATTERN = re.compile(r"\*\*Tool name:\*\*\s*`([^`]+)`")
# Fallback: "Tool name: `X`" without bold
TOOL_NAME_LOOSE = re.compile(r"Tool name:\s*`([^`]+)`")

# Reference header metadata patterns (top of REFERENCE.md)
REFERENCE_SOURCE_PATTERN = re.compile(r"^Vendored from:\s*(\S.+)$", re.MULTILINE)
REFERENCE_VERSION_PATTERN = re.compile(r"^SDK version:\s*(.+)$", re.MULTILINE)
REFERENCE_SNAPSHOT_PATTERN = re.compile(r"^Snapshot date:\s*(\d{4}-\d{2}-\d{2})$", re.MULTILINE)
REFERENCE_HEADER_SCAN_LINES = 60


def utc_now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def should_require_sdk(strict: bool = False) -> bool:
    """Return True if missing SDK should fail checks."""
    if strict:
        return True
    if os.getenv("SWARM_STRICT_SDK_CHECK", "").lower() in {"1", "true", "yes"}:
        return True
    return os.getenv("CI", "").lower() in {"1", "true", "yes"}


def try_import_sdk() -> Tuple[Optional[str], Optional[str], Optional[Any]]:
    """
    Try to import SDK, preferring official package over legacy.

    Returns:
        Tuple of (module_name, dist_name, module_obj) or (None, None, None) if not found.
    """
    for module_name, dist_name in IMPORT_CANDIDATES:
        try:
            mod = import_module(module_name)
            return module_name, dist_name, mod
        except ImportError:
            continue
    return None, None, None


def safe_get_dist_version(dist_name: str) -> Optional[str]:
    """Get distribution version, returning None if not found."""
    try:
        return dist_version(dist_name)
    except PackageNotFoundError:
        return None


def scrub_unstable_repr(s: Optional[str]) -> Optional[str]:
    """Scrub unstable object representations (addresses, stream names)."""
    if not s:
        return s
    # Scrub hex addresses
    s = re.sub(r" at 0x[0-9a-fA-F]+", " at 0x...", s)
    
    # If the whole string is an unstable object repr (from dataclass field default)
    if (s.startswith("<_io.TextIOWrapper") or 
        s.startswith("<EncodedFile") or 
        s.startswith("<tempfile._TemporaryFileWrapper")):
        return "<stream>"

    # If it's embedded in a signature (e.g. debug_stderr: Any = <...>)
    # Signature version: matches until the next parameter or end of signature
    s = re.sub(r"debug_stderr: Any = <[^,)]+>", "debug_stderr: Any = <stream>", s)
    
    return s


def format_signature(obj: Any) -> Optional[str]:
    """Get string representation of function/method signature."""
    try:
        sig = str(inspect.signature(obj))
        return scrub_unstable_repr(sig)
    except Exception:
        return None


def dataclass_fields_manifest(cls: Any) -> Optional[List[Dict[str, Any]]]:
    """Extract dataclass fields as manifest entries."""
    if not dataclasses.is_dataclass(cls):
        return None
    out: List[Dict[str, Any]] = []
    for f in dataclasses.fields(cls):
        out.append({
            "name": f.name,
            "type": repr(f.type),
            "default": scrub_unstable_repr(None if f.default is dataclasses.MISSING else repr(f.default)),
            "default_factory": (
                None if f.default_factory is dataclasses.MISSING
                else repr(f.default_factory)
            ),
        })
    return out


def object_manifest(name: str, obj: Any) -> Dict[str, Any]:
    """Build manifest entry for a single exported object."""
    kind = "unknown"
    if inspect.isfunction(obj):
        kind = "function"
    elif inspect.isclass(obj):
        kind = "class"
    elif inspect.ismethod(obj):
        kind = "method"
    elif callable(obj):
        kind = "callable"

    # Get first line of docstring for compact manifest
    doc = inspect.getdoc(obj) or ""
    doc_first = doc.split("\n")[0].strip() if doc else None

    entry: Dict[str, Any] = {
        "name": name,
        "kind": kind,
        "signature": format_signature(obj),
        "doc_first_line": doc_first[:200] if doc_first else None,  # Cap for stability
    }

    if inspect.isclass(obj):
        entry["dataclass_fields"] = dataclass_fields_manifest(obj)
        # Public methods (names only) for drift detection
        methods = sorted({
            m for m, v in inspect.getmembers(obj)
            if (inspect.isfunction(v) or inspect.ismethod(v)) and not m.startswith("_")
        })
        entry["methods"] = methods

    return entry


def build_api_manifest(mod: Any) -> Dict[str, Any]:
    """Build complete API manifest from module."""
    exported: Dict[str, Any] = {}

    for name in dir(mod):
        if name.startswith("_"):
            continue
        try:
            obj = getattr(mod, name)
        except Exception:
            continue
        # Skip submodules; we want top-level API surface
        if inspect.ismodule(obj):
            continue
        exported[name] = object_manifest(name, obj)

    return {
        "generated_at": utc_now_iso(),
        "module": getattr(mod, "__name__", "<unknown>"),
        "exported": exported,
        "export_count": len(exported),
    }


def extract_tool_names_from_reference(reference_path: Path) -> List[str]:
    """Extract tool names from reference markdown file."""
    if not reference_path.exists():
        return []

    text = reference_path.read_text(encoding="utf-8")

    # Try primary pattern first
    names = TOOL_NAME_PATTERN.findall(text)

    # Fallback to looser pattern if nothing found
    if not names:
        names = TOOL_NAME_LOOSE.findall(text)

    # Normalize and dedupe
    cleaned = sorted({n.strip() for n in names if n.strip()})
    return cleaned


def reference_sha256(text: str) -> str:
    """Return SHA256 of reference text for drift detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_reference_header(text: str) -> Dict[str, Optional[str]]:
    """Parse header metadata from REFERENCE.md."""
    header_text = "\n".join(text.splitlines()[:REFERENCE_HEADER_SCAN_LINES])

    source_match = REFERENCE_SOURCE_PATTERN.search(header_text)
    version_match = REFERENCE_VERSION_PATTERN.search(header_text)
    snapshot_match = REFERENCE_SNAPSHOT_PATTERN.search(header_text)

    sdk_distribution = None
    sdk_version = None
    sdk_version_raw = None

    if version_match:
        sdk_version_raw = version_match.group(1).strip()
        if sdk_version_raw.startswith("`") and sdk_version_raw.endswith("`"):
            sdk_version_raw = sdk_version_raw[1:-1].strip()
        if "==" in sdk_version_raw:
            sdk_distribution, sdk_version = [
                part.strip() for part in sdk_version_raw.split("==", 1)
            ]
        else:
            parts = sdk_version_raw.split()
            if len(parts) >= 2:
                sdk_distribution, sdk_version = parts[0].strip(), parts[1].strip()

    return {
        "reference_source": source_match.group(1).strip() if source_match else None,
        "reference_snapshot_date": snapshot_match.group(1).strip() if snapshot_match else None,
        "reference_sdk_distribution": sdk_distribution,
        "reference_sdk_version": sdk_version,
        "reference_sdk_version_raw": sdk_version_raw,
    }


def extract_reference_metadata(reference_path: Path) -> Dict[str, Optional[str]]:
    """Extract header metadata and hash from REFERENCE.md."""
    if not reference_path.exists():
        return {
            "reference_sha256": None,
            "reference_source": None,
            "reference_snapshot_date": None,
            "reference_sdk_distribution": None,
            "reference_sdk_version": None,
        }

    text = reference_path.read_text(encoding="utf-8")
    meta = _parse_reference_header(text)
    meta["reference_sha256"] = reference_sha256(text)
    return meta


def write_json(path: Path, data: Any) -> None:
    """Write JSON to file with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8"
    )


def read_json(path: Path) -> Any:
    """Read JSON from file."""
    return json.loads(path.read_text(encoding="utf-8"))


def json_equal(a: Any, b: Any, ignore_keys: Optional[List[str]] = None) -> bool:
    """Compare JSON structures, optionally ignoring certain keys."""
    if ignore_keys:
        a = {k: v for k, v in a.items() if k not in ignore_keys} if isinstance(a, dict) else a
        b = {k: v for k, v in b.items() if k not in ignore_keys} if isinstance(b, dict) else b
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def cmd_status() -> int:
    """Show current SDK status without modifying files."""
    print("Claude Agent SDK Vendor Status")
    print("=" * 40)

    # Check import
    module_name, dist_name, mod = try_import_sdk()
    if mod is None:
        print("\nSDK Status: NOT INSTALLED")
        print("  Neither claude_agent_sdk nor claude_code_sdk is available.")
        print("  Install with: pip install claude-agent-sdk")
        return 1

    ver = safe_get_dist_version(dist_name) if dist_name else None
    print(f"\nSDK Status: INSTALLED")
    print(f"  Import module: {module_name}")
    print(f"  Distribution:  {dist_name}")
    print(f"  Version:       {ver or 'unknown'}")

    # Check vendored files
    print("\nVendored Files:")
    for path in [VERSION_JSON, API_MANIFEST_JSON, TOOLS_MANIFEST_JSON]:
        rel_path = path.relative_to(REPO_ROOT)
        if path.exists():
            print(f"  {rel_path}: EXISTS")
        else:
            print(f"  {rel_path}: MISSING")

    if REFERENCE_MD.exists():
        print(f"  {REFERENCE_MD.relative_to(REPO_ROOT)}: EXISTS")
        tool_names = extract_tool_names_from_reference(REFERENCE_MD)
        print(f"    Tools extracted: {len(tool_names)}")
    else:
        print(f"  {REFERENCE_MD.relative_to(REPO_ROOT)}: MISSING (optional)")

    # Check for drift
    if VERSION_JSON.exists():
        try:
            cur_version = read_json(VERSION_JSON)
            if cur_version.get("version") != ver:
                print(f"\nDRIFT DETECTED:")
                print(f"  Vendored version: {cur_version.get('version')}")
                print(f"  Installed version: {ver}")
                print("  Run: make vendor-agent-sdk")
        except Exception as e:
            print(f"\nWarning: Could not read VERSION.json: {e}")

    print()
    return 0


def cmd_write() -> int:
    """Generate and write vendor artifacts."""
    print("Vendoring Claude Agent SDK API surface...")

    # Try import
    module_name, dist_name, mod = try_import_sdk()
    if mod is None:
        print("ERROR: Claude SDK not installed.")
        print("  Install with: pip install claude-agent-sdk")
        print("  Or: pip install claude-code-sdk (legacy)")
        return 1

    ver = safe_get_dist_version(dist_name) if dist_name else None

    # Build payloads
    version_payload = {
        "generated_at": utc_now_iso(),
        "import_module": module_name,
        "distribution": dist_name,
        "version": ver,
        "python": sys.version.split()[0],
    }

    api_payload = build_api_manifest(mod)

    # Extract tool names and reference metadata
    tool_names = extract_tool_names_from_reference(REFERENCE_MD)
    reference_meta = extract_reference_metadata(REFERENCE_MD)
    tools_payload = {
        "generated_at": utc_now_iso(),
        "tool_names": tool_names,
        "count": len(tool_names),
        "source": str(REFERENCE_MD.relative_to(REPO_ROOT)) if REFERENCE_MD.exists() else None,
        "reference_sha256": reference_meta.get("reference_sha256"),
        "reference_source": reference_meta.get("reference_source"),
        "reference_snapshot_date": reference_meta.get("reference_snapshot_date"),
        "reference_sdk_distribution": reference_meta.get("reference_sdk_distribution"),
        "reference_sdk_version": reference_meta.get("reference_sdk_version"),
        "note": (
            "Extracted from REFERENCE.md"
            if tool_names
            else "No tool names found in REFERENCE.md"
            if REFERENCE_MD.exists()
            else "No REFERENCE.md found"
        ),
    }

    # Write files
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    write_json(VERSION_JSON, version_payload)
    write_json(API_MANIFEST_JSON, api_payload)
    write_json(TOOLS_MANIFEST_JSON, tools_payload)

    print(f"OK Wrote:")
    print(f"  - {VERSION_JSON.relative_to(REPO_ROOT)}")
    print(f"  - {API_MANIFEST_JSON.relative_to(REPO_ROOT)}")
    print(f"  - {TOOLS_MANIFEST_JSON.relative_to(REPO_ROOT)}")
    print(f"\nSDK: {module_name} ({dist_name} {ver})")
    print(f"API exports: {api_payload['export_count']}")
    print(f"Tools extracted: {len(tool_names)}")

    return 0


def cmd_check(strict: bool = False) -> int:
    """
    Verify vendored artifacts match installed SDK.

    IMPORTANT: This is a pure read-only operation. It NEVER writes files.
    All comparisons use json_equal() with ignore_keys=["generated_at"] to ensure
    deterministic results regardless of when the check is run. The generated_at
    timestamps in expected payloads are only used for structural completeness
    and are stripped before comparison.
    """
    print("Checking vendored Claude Agent SDK artifacts...")

    # Check SDK is installed
    module_name, dist_name, mod = try_import_sdk()
    if mod is None:
        if should_require_sdk(strict=strict):
            print("FAIL: SDK not installed, cannot verify.")
            print("  Install with: pip install claude-agent-sdk")
            return 3
        print("SKIP: SDK not installed, cannot verify.")
        return 0  # Not an error - SDK is optional

    ver = safe_get_dist_version(dist_name) if dist_name else None

    # Check files exist
    missing = [p for p in [VERSION_JSON, API_MANIFEST_JSON, TOOLS_MANIFEST_JSON] if not p.exists()]
    if missing:
        print("FAIL: Missing vendored files:")
        for p in missing:
            print(f"  - {p.relative_to(REPO_ROOT)}")
        print("\nRun: make vendor-agent-sdk")
        return 2

    # Build expected payloads
    version_payload = {
        "generated_at": utc_now_iso(),  # Will be ignored in comparison
        "import_module": module_name,
        "distribution": dist_name,
        "version": ver,
        "python": sys.version.split()[0],
    }

    api_payload = build_api_manifest(mod)
    tool_names = extract_tool_names_from_reference(REFERENCE_MD)
    reference_meta = extract_reference_metadata(REFERENCE_MD)
    tools_payload = {
        "generated_at": utc_now_iso(),
        "tool_names": tool_names,
        "count": len(tool_names),
        "source": str(REFERENCE_MD.relative_to(REPO_ROOT)) if REFERENCE_MD.exists() else None,
        "reference_sha256": reference_meta.get("reference_sha256"),
        "reference_source": reference_meta.get("reference_source"),
        "reference_snapshot_date": reference_meta.get("reference_snapshot_date"),
        "reference_sdk_distribution": reference_meta.get("reference_sdk_distribution"),
        "reference_sdk_version": reference_meta.get("reference_sdk_version"),
        "note": (
            "Extracted from REFERENCE.md"
            if tool_names
            else "No tool names found in REFERENCE.md"
            if REFERENCE_MD.exists()
            else "No REFERENCE.md found"
        ),
    }

    # Compare (ignoring generated_at timestamp)
    ok = True
    cur_version = read_json(VERSION_JSON)
    cur_api = read_json(API_MANIFEST_JSON)
    cur_tools = read_json(TOOLS_MANIFEST_JSON)

    # Version check (ignore generated_at)
    if not json_equal(cur_version, version_payload, ignore_keys=["generated_at"]):
        ok = False
        print(f"FAIL: {VERSION_JSON.relative_to(REPO_ROOT)} is stale")
        if cur_version.get("version") != version_payload.get("version"):
            print(f"  Vendored: {cur_version.get('version')}")
            print(f"  Installed: {version_payload.get('version')}")

    # Reference header check (ties REFERENCE.md to VERSION.json)
    if REFERENCE_MD.exists():
        ref_dist = reference_meta.get("reference_sdk_distribution")
        ref_ver = reference_meta.get("reference_sdk_version")
        if not ref_dist or not ref_ver:
            ok = False
            print(f"FAIL: {REFERENCE_MD.relative_to(REPO_ROOT)} missing SDK version header")
        else:
            if ref_dist != cur_version.get("distribution") or ref_ver != cur_version.get("version"):
                ok = False
                print(f"FAIL: {REFERENCE_MD.relative_to(REPO_ROOT)} version mismatch")
                print(f"  REFERENCE: {ref_dist} {ref_ver}")
                print(f"  VERSION.json: {cur_version.get('distribution')} {cur_version.get('version')}")

    # API check (ignore generated_at)
    if not json_equal(cur_api, api_payload, ignore_keys=["generated_at"]):
        ok = False
        print(f"FAIL: {API_MANIFEST_JSON.relative_to(REPO_ROOT)} is stale")
        
        # Show what changed
        cur_exports = set(cur_api.get("exported", {}).keys())
        new_exports = set(api_payload.get("exported", {}).keys())
        added = new_exports - cur_exports
        removed = cur_exports - new_exports
        if added:
            print(f"  New exports: {added}")
        if removed:
            print(f"  Removed exports: {removed}")

    # Tools check (ignore generated_at)
    if not json_equal(cur_tools, tools_payload, ignore_keys=["generated_at"]):
        ok = False
        print(f"FAIL: {TOOLS_MANIFEST_JSON.relative_to(REPO_ROOT)} is stale")

    if not ok:
        print("\nRun: make vendor-agent-sdk")
        return 1

    print("OK: Vendored Agent SDK artifacts are current.")
    print(f"SDK: {module_name} ({dist_name} {ver})")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Vendor Claude Agent SDK API surface for offline reference",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --status    Show current SDK and vendor status
  %(prog)s --write     Generate/update vendor artifacts
  %(prog)s --check     Verify vendor artifacts are current

The vendored artifacts enable:
  - Offline documentation reference
  - Drift detection between SDK versions
  - Contract tests without network access
        """,
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show SDK and vendor status (default action)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write/update vendor artifacts from installed SDK",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify vendor artifacts match installed SDK",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail check if SDK is not installed (also implied in CI)",
    )

    args = parser.parse_args()

    # Default to status if no action specified
    if not any([args.status, args.write, args.check]):
        args.status = True

    if args.write:
        return cmd_write()
    elif args.check:
        return cmd_check(strict=args.strict)
    else:
        return cmd_status()


if __name__ == "__main__":
    raise SystemExit(main())
