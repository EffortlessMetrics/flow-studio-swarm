#!/usr/bin/env python3
"""
generate_meta_docs.py - Generate documentation snippets from swarm metadata.

This script reads swarm metadata from swarm/meta.py and updates documentation
files that contain generated sections. This eliminates manual maintenance of
counts like "48 agents", "16 steps", "4 skills" across documentation.

## Generated Section Markers

Documentation files can include generated sections using markers:

    <!-- META:AGENT_COUNTS -->
    This content will be replaced
    <!-- /META:AGENT_COUNTS -->

Available markers:
- META:AGENT_COUNTS - Agent count summary (e.g., "48 agents (3 built-in + 45 domain)")
- META:SELFTEST_COUNTS - Selftest step counts (e.g., "16 steps (1 KERNEL + 13 GOVERNANCE + 2 OPTIONAL)")
- META:SKILLS_COUNTS - Skills count and list
- META:FULL_SUMMARY - Complete metadata summary

## Usage

    # Preview changes (dry-run)
    python swarm/tools/generate_meta_docs.py --dry-run

    # Apply changes
    python swarm/tools/generate_meta_docs.py

    # Check if docs are up-to-date (for CI)
    python swarm/tools/generate_meta_docs.py --check

    # JSON output
    python swarm/tools/generate_meta_docs.py --json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from meta import compute_meta


def get_repo_root() -> Path:
    """Find repository root."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists() or (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path.cwd()


# Files that contain generated sections
GENERATED_DOCS = [
    "README.md",
    "CLAUDE.md",
    "ARCHITECTURE.md",
    "swarm/AGENTS.md",
    "swarm/SELFTEST_SYSTEM.md",
    "docs/WHITEPAPER.md",
    "docs/AGENT_OPS.md",
]


def generate_agent_counts(meta: Dict[str, Any]) -> str:
    """Generate agent counts snippet."""
    return (
        f"**Total: {meta['agents']['total']} agents** "
        f"({meta['agents']['built_in']} built-in + {meta['agents']['domain']} domain)"
    )


def generate_selftest_counts(meta: Dict[str, Any]) -> str:
    """Generate selftest counts snippet."""
    tiers = meta["selftest"]["tiers"]
    return (
        f"**{meta['selftest']['total']} selftest steps** "
        f"({tiers['KERNEL']} KERNEL + {tiers['GOVERNANCE']} GOVERNANCE + {tiers['OPTIONAL']} OPTIONAL)"
    )


def generate_skills_counts(meta: Dict[str, Any]) -> str:
    """Generate skills counts snippet."""
    skills_list = ", ".join(meta["skills"]["list"])
    return f"**{meta['skills']['count']} skills** ({skills_list})"


def generate_full_summary(meta: Dict[str, Any]) -> str:
    """Generate full metadata summary."""
    tiers = meta["selftest"]["tiers"]
    skills_list = ", ".join(meta["skills"]["list"])
    return f"""**Swarm Metadata** (auto-generated from configuration)

- **Agents**: {meta["agents"]["total"]} total ({meta["agents"]["built_in"]} built-in + {meta["agents"]["domain"]} domain)
- **Selftest**: {meta["selftest"]["total"]} steps ({tiers["KERNEL"]} KERNEL + {tiers["GOVERNANCE"]} GOVERNANCE + {tiers["OPTIONAL"]} OPTIONAL)
- **Skills**: {meta["skills"]["count"]} ({skills_list})
- **Flows**: {meta["flows"]["sdlc_count"]} SDLC flows"""


# Marker name -> generator function
GENERATORS = {
    "AGENT_COUNTS": generate_agent_counts,
    "SELFTEST_COUNTS": generate_selftest_counts,
    "SKILLS_COUNTS": generate_skills_counts,
    "FULL_SUMMARY": generate_full_summary,
}


def find_markers(content: str) -> List[Tuple[str, int, int]]:
    """
    Find all META markers in content.

    Returns list of (marker_name, start_pos, end_pos) tuples.
    """
    markers = []
    pattern = re.compile(r"<!-- META:(\w+) -->\n(.*?)<!-- /META:\1 -->", re.DOTALL)
    for match in pattern.finditer(content):
        markers.append(
            (
                match.group(1),  # marker name
                match.start(),  # start position
                match.end(),  # end position
            )
        )
    return markers


def update_markers(content: str, meta: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Update all META markers in content with generated values.

    Returns (updated_content, list of changes made).
    """
    changes = []

    # Process markers in reverse order to preserve positions
    markers = find_markers(content)
    for marker_name, start, end in reversed(markers):
        if marker_name not in GENERATORS:
            continue

        generator = GENERATORS[marker_name]
        new_content = generator(meta)

        # Build replacement string
        replacement = f"<!-- META:{marker_name} -->\n{new_content}\n<!-- /META:{marker_name} -->"

        # Check if content changed
        old_section = content[start:end]
        if old_section != replacement:
            changes.append(
                {
                    "marker": marker_name,
                    "old_length": len(old_section),
                    "new_length": len(replacement),
                }
            )

        content = content[:start] + replacement + content[end:]

    return content, changes


def process_file(
    file_path: Path, meta: Dict[str, Any], dry_run: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Process a single documentation file.

    Returns dict with file info and changes, or None if no markers found.
    """
    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"file": str(file_path), "error": str(e)}

    # Check if file has any markers
    markers = find_markers(content)
    if not markers:
        return None

    # Update content
    updated_content, changes = update_markers(content, meta)

    result = {
        "file": str(file_path),
        "markers_found": len(markers),
        "changes": changes,
        "modified": len(changes) > 0,
    }

    # Write if not dry-run and content changed
    if not dry_run and updated_content != content:
        file_path.write_text(updated_content, encoding="utf-8")
        result["written"] = True
    else:
        result["written"] = False

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate documentation from swarm metadata")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing files"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check if docs are up-to-date (exit 1 if not)"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    repo_root = get_repo_root()
    meta = compute_meta()

    results = []
    files_modified = 0

    for rel_path in GENERATED_DOCS:
        file_path = repo_root / rel_path
        result = process_file(file_path, meta, dry_run=args.dry_run or args.check)
        if result:
            results.append(result)
            if result.get("modified"):
                files_modified += 1

    # Output results
    if args.json:
        output = {
            "meta": meta,
            "files_scanned": len(GENERATED_DOCS),
            "files_with_markers": len(results),
            "files_modified": files_modified,
            "results": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print("Meta Doc Generator")
        print("=" * 50)
        print()
        print("Computed metadata:")
        print(
            f"  Agents: {meta['agents']['total']} ({meta['agents']['built_in']} built-in + {meta['agents']['domain']} domain)"
        )
        print(f"  Selftest: {meta['selftest']['total']} steps")
        print(f"  Skills: {meta['skills']['count']}")
        print()

        if not results:
            print("No files with META markers found.")
            print()
            print("To add generated sections to a doc, use markers like:")
            print("  <!-- META:AGENT_COUNTS -->")
            print("  <!-- /META:AGENT_COUNTS -->")
            return 0

        print(f"Scanned {len(GENERATED_DOCS)} files, found {len(results)} with markers")
        print()

        for result in results:
            file_path = result["file"]
            try:
                rel_path = Path(file_path).relative_to(repo_root)
            except ValueError:
                rel_path = file_path

            if result.get("error"):
                print(f"  {rel_path}: ERROR - {result['error']}")
            elif result.get("modified"):
                marker_names = [c["marker"] for c in result["changes"]]
                status = "would update" if (args.dry_run or args.check) else "updated"
                print(f"  {rel_path}: {status} ({', '.join(marker_names)})")
            elif args.verbose:
                print(f"  {rel_path}: up-to-date ({result['markers_found']} markers)")

        print()

        if args.check and files_modified > 0:
            print(f"ERROR: {files_modified} file(s) need updating. Run without --check to update.")
            return 1
        elif args.dry_run:
            print(f"Dry run complete. {files_modified} file(s) would be modified.")
        else:
            print(f"Done. {files_modified} file(s) updated.")

    return 1 if (args.check and files_modified > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
