# swarm/tools/validation/validators/flows/documentation.py
"""Flow documentation completeness validation.

Validates that each flow config has corresponding markdown documentation
with the required autogen markers.
"""

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import ROOT, FLOW_SPECS_DIR, FLOWS_CONFIG_DIR


def validate_flow_documentation_completeness() -> ValidationResult:
    """
    Validate that each flow config has corresponding markdown documentation.

    Invariant 4: Documentation completeness - each flow has a markdown file with autogen markers
    """
    result = ValidationResult()

    if not FLOWS_CONFIG_DIR.is_dir():
        return result

    for config_file in sorted(FLOWS_CONFIG_DIR.glob("*.yaml")):
        flow_id = config_file.stem

        # Check for corresponding markdown file
        doc_file = FLOW_SPECS_DIR / f"flow-{flow_id}.md"

        if not doc_file.is_file():
            location = f"swarm/config/flows/{flow_id}.yaml"

            result.add_error(
                "FLOW",
                location,
                f"Flow '{flow_id}' config exists but documentation file is missing",
                f"Create {doc_file.relative_to(ROOT)} with flow specification",
                file_path=str(config_file)
            )
            continue

        # Check for autogen markers in markdown
        try:
            content = doc_file.read_text(encoding="utf-8")
            has_start = "FLOW AUTOGEN START" in content or "<!-- FLOW AUTOGEN START" in content
            has_end = "FLOW AUTOGEN END" in content or "FLOW AUTOGEN END -->" in content

            if not (has_start and has_end):
                location = f"{doc_file.relative_to(ROOT)}"

                result.add_error(
                    "FLOW",
                    location,
                    "Flow documentation missing autogen markers",
                    f"Add '<!-- FLOW AUTOGEN START -->' and '<!-- FLOW AUTOGEN END -->' markers to {location}",
                    file_path=str(doc_file)
                )
        except Exception as e:
            result.add_error(
                "FLOW",
                str(doc_file.relative_to(ROOT)),
                f"Failed to read flow documentation: {e}",
                "Check file permissions and encoding",
                file_path=str(doc_file)
            )

    return result
