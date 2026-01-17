# swarm/tools/validation/reporting/markdown_output.py
"""Markdown output formatter for validation results."""

from datetime import datetime, timezone

from swarm.validator import ValidationResult


def build_report_markdown(result: ValidationResult) -> str:
    """Build markdown validation report.

    Generates a human-readable markdown report with title, status,
    checks performed, and any errors/warnings.

    Args:
        result: The validation result containing errors and warnings

    Returns:
        Markdown-formatted string with the validation report
    """
    lines: list[str] = []

    # Title and summary
    lines.append("# Swarm Validation Report")
    lines.append("")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"**Status**: {'PASSED' if not result.has_errors() else 'FAILED'}")
    lines.append("")

    # Checks performed
    checks = [
        ("Agent Registry Bijection", "BIJECTION"),
        ("Frontmatter Validation", "FRONTMATTER"),
        ("Flow References", "REFERENCE"),
        ("Skills Validation", "SKILL"),
        ("RUN_BASE Paths", "RUNBASE"),
    ]

    lines.append("## Checks Performed")
    lines.append("")
    for name, error_type in checks:
        has_error = any(e.error_type == error_type for e in result.errors)
        marker = "[ ]" if has_error else "[x]"
        lines.append(f"- {marker} {name}")
    lines.append("")

    # Errors section
    error_count = len(result.errors)
    lines.append(f"## Errors ({error_count})")
    lines.append("")

    if error_count == 0:
        lines.append("_No errors found._")
    else:
        for error in result.sorted_errors():
            lines.append(f"### {error.error_type}")
            lines.append(f"**Location**: {error.location}")
            lines.append(f"**Error**: {error.problem}")
            if error.fix_action:
                lines.append(f"**Fix**: {error.fix_action}")
            lines.append("")

    lines.append("")

    # Warnings section
    warning_count = len(result.warnings)
    lines.append(f"## Warnings ({warning_count})")
    lines.append("")

    if warning_count == 0:
        lines.append("_No warnings._")
    else:
        for warning in result.sorted_warnings():
            lines.append(f"### {warning.error_type}")
            lines.append(f"**Location**: {warning.location}")
            lines.append(f"**Warning**: {warning.problem}")
            if warning.fix_action:
                lines.append(f"**Fix**: {warning.fix_action}")
            lines.append("")

    return "\n".join(lines)
