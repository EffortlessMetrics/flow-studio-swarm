# swarm/tools/validation/validators/runbase.py
"""
FR-005: RUN_BASE Path Validation

Validates that flow specs use RUN_BASE placeholder, not hardcoded paths.

Checks:
- No hardcoded swarm/runs/<run-id>/ paths
- RUN_BASE placeholder is correctly formatted (no $, {}, etc.)
"""

import re

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import ROOT, FLOW_SPECS_DIR


def validate_runbase_paths() -> ValidationResult:
    """
    Validate that flow specs use RUN_BASE placeholder, not hardcoded paths.

    Checks:
    - No hardcoded swarm/runs/<run-id>/ paths
    - RUN_BASE placeholder is correctly formatted (no $, {}, etc.)
    """
    result = ValidationResult()

    if not FLOW_SPECS_DIR.is_dir():
        return result

    # Patterns to detect
    # Match swarm/runs/SOMETHING/ where SOMETHING is alphanumeric, hyphens, underscores, or angle/curly brackets
    # Handles: swarm/runs/run-123/, swarm/runs/<run-id>/, swarm/runs/{run-id}/
    hardcoded_pattern = re.compile(r"swarm/runs/[a-zA-Z0-9_\-<>{}]+/")

    # Malformed RUN_BASE patterns:
    # - $RUN_BASE (shell variable syntax)
    # - {RUN_BASE} (template variable syntax without slash)
    # - RUN_BASE without trailing slash (e.g., RUN_BASEsignal)
    # - run_base or run-base (lowercase or hyphenated, case-sensitive check)
    malformed_runbase = re.compile(r"(\$RUN_BASE|RUN_BASE\}|RUN_BASE[a-zA-Z_]|\{RUN_BASE[^/]|run_base/)")

    for flow_path in sorted(FLOW_SPECS_DIR.glob("*.md")):
        if flow_path.is_symlink():
            # Skip symlinks: validation only applies to real files
            continue

        rel_path = flow_path.relative_to(ROOT)
        content = flow_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        in_code_block = False

        for i, line in enumerate(lines, start=1):
            stripped_line = line.strip()
            # Track code blocks
            if stripped_line.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Skip comments (both Markdown and HTML)
            if stripped_line.startswith("#") or stripped_line.startswith("<!--"):
                continue

            # Check for hardcoded paths
            if hardcoded_pattern.search(line):
                result.add_error(
                    "RUNBASE",
                    f"{rel_path}:line {i}",
                    "contains hardcoded path 'swarm/runs/<run-id>/'; should use RUN_BASE placeholder",
                    "Replace hardcoded path with 'RUN_BASE/<flow>/' in artifact instructions",
                    line_number=i,
                    file_path=str(flow_path)
                )

            # Check for malformed RUN_BASE - iterate over all matches to include actual text
            for match in malformed_runbase.finditer(line):
                bad_text = match.group(0)
                result.add_error(
                    "RUNBASE",
                    f"{rel_path}:line {i}",
                    f"malformed RUN_BASE placeholder '{bad_text}' (should be 'RUN_BASE/<flow>/', not '$RUN_BASE', '{{RUN_BASE}}', or 'RUN_BASEsignal')",
                    "Use 'RUN_BASE/<flow>/' with forward slash; valid examples: RUN_BASE/signal/, RUN_BASE/plan/, RUN_BASE/build/",
                    line_number=i,
                    file_path=str(flow_path)
                )

    return result
