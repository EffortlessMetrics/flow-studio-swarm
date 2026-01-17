# swarm/tools/validation/validators/capabilities.py
"""
FR-007: Capability Registry Validation

Validates the capability registry for evidence discipline.

Checks:
- implemented capabilities have >=1 test pointer
- implemented capabilities have >=1 code pointer
- @cap:<id> tags in BDD reference capabilities that exist in registry
- aspirational capabilities are not claimed as implemented

This validation ensures that capability claims have evidence,
preventing "narrative drift" where docs claim capabilities
that aren't backed by code or tests.
"""

import re
from pathlib import Path
from typing import Set

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import ROOT


def validate_capability_registry() -> ValidationResult:
    """
    Validate the capability registry for evidence discipline.

    FR-007: Capability Registry
    Checks:
    - implemented capabilities have >=1 test pointer
    - implemented capabilities have >=1 code pointer
    - @cap:<id> tags in BDD reference capabilities that exist in registry
    - aspirational capabilities are not claimed as implemented

    This validation ensures that capability claims have evidence,
    preventing "narrative drift" where docs claim capabilities
    that aren't backed by code or tests.
    """
    result = ValidationResult()

    # Check if capability registry exists
    registry_path = ROOT / "specs" / "capabilities.yaml"
    if not registry_path.exists():
        result.add_warning(
            "CAPABILITY",
            "specs/capabilities.yaml",
            "capability registry not found (optional file)",
            "Create specs/capabilities.yaml to track capability claims with evidence",
            file_path=str(registry_path)
        )
        return result

    # Parse capability registry (uses PyYAML, not SimpleYAMLParser which is for frontmatter)
    try:
        import yaml
        content = registry_path.read_text(encoding="utf-8")
        registry = yaml.safe_load(content)
    except ImportError:
        result.add_warning(
            "CAPABILITY",
            "specs/capabilities.yaml",
            "PyYAML not installed; skipping capability registry validation",
            "Install PyYAML: pip install pyyaml",
            file_path=str(registry_path)
        )
        return result
    except Exception as e:
        result.add_error(
            "CAPABILITY",
            "specs/capabilities.yaml",
            f"failed to parse capability registry: {e}",
            "Fix YAML syntax in specs/capabilities.yaml",
            file_path=str(registry_path)
        )
        return result

    # Collect all capability IDs
    cap_ids: Set[str] = set()
    aspirational_ids: Set[str] = set()

    surfaces = registry.get("surfaces", {})
    if not isinstance(surfaces, dict):
        result.add_error(
            "CAPABILITY",
            "specs/capabilities.yaml",
            "'surfaces' must be a dict",
            "Fix structure: surfaces should map surface names to capability lists",
            file_path=str(registry_path)
        )
        return result

    for surface_key, surface_data in surfaces.items():
        if not isinstance(surface_data, dict):
            continue

        capabilities = surface_data.get("capabilities", [])
        if not isinstance(capabilities, list):
            continue

        for cap in capabilities:
            if not isinstance(cap, dict):
                continue

            cap_id = cap.get("id", "")
            status = cap.get("status", "")
            evidence = cap.get("evidence", {})

            if not cap_id:
                result.add_warning(
                    "CAPABILITY",
                    f"specs/capabilities.yaml:{surface_key}",
                    "capability missing 'id' field",
                    "Add 'id' field to capability entry",
                    file_path=str(registry_path)
                )
                continue

            cap_ids.add(cap_id)

            if status == "aspirational":
                aspirational_ids.add(cap_id)
                # Aspirational caps don't need code/test evidence
                continue

            if status == "implemented":
                # Must have test evidence
                tests = evidence.get("tests", [])
                if not tests:
                    result.add_error(
                        "CAPABILITY",
                        f"specs/capabilities.yaml:{cap_id}",
                        f"capability '{cap_id}' is 'implemented' but has no test evidence",
                        "Add 'tests' evidence pointers or change status to 'supported'",
                        file_path=str(registry_path)
                    )

                # Must have code evidence
                code = evidence.get("code", [])
                if not code:
                    result.add_error(
                        "CAPABILITY",
                        f"specs/capabilities.yaml:{cap_id}",
                        f"capability '{cap_id}' is 'implemented' but has no code evidence",
                        "Add 'code' evidence pointers with path and symbol",
                        file_path=str(registry_path)
                    )

    # Check BDD @cap: tags reference capabilities that exist
    features_dir = ROOT / "features"
    if features_dir.is_dir():
        for feature_file in features_dir.glob("*.feature"):
            try:
                feature_content = feature_file.read_text(encoding="utf-8")
                # Find all @cap:<id> tags
                cap_tag_pattern = re.compile(r"@cap:([a-z0-9_.]+)")
                for match in cap_tag_pattern.finditer(feature_content):
                    tag_id = match.group(1)
                    if tag_id not in cap_ids:
                        # Find line number
                        line_num = feature_content[:match.start()].count('\n') + 1
                        result.add_error(
                            "CAPABILITY",
                            f"{feature_file.name}:line {line_num}",
                            f"@cap:{tag_id} references capability not in registry",
                            f"Add '{tag_id}' to specs/capabilities.yaml or fix tag",
                            line_number=line_num,
                            file_path=str(feature_file)
                        )
            except (OSError, UnicodeDecodeError):
                pass  # Skip files that can't be read

    return result
