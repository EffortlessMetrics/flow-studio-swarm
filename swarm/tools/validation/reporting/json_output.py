# swarm/tools/validation/reporting/json_output.py
"""JSON output formatters for validation results."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

from swarm.validator import ValidationResult

from ..constants import BUILT_IN_AGENTS
from ..helpers import AGENTS_DIR, FLOW_SPECS_DIR, FLOWS_CONFIG_DIR, ROOT


def build_detailed_json_output(
    result: ValidationResult,
    registry: Dict[str, Dict[str, Any]],
    parse_flow_config: Callable[[Path], Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build detailed JSON output with per-agent/flow/step breakdown.

    The output format provides machine-readable validation results
    that can be consumed by Flow Studio for governance overlays.

    Args:
        result: The validation result containing errors and warnings
        registry: The agent registry dictionary
        parse_flow_config: Function to parse flow config files

    Returns:
        Dictionary with detailed validation output
    """
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Build agents section with per-agent check status
    agents_data: Dict[str, Any] = {}
    for agent_key in sorted(registry.keys()):
        if agent_key in BUILT_IN_AGENTS:
            continue

        meta = registry[agent_key]
        if meta.get("source") != "project/user":
            continue

        agent_file = AGENTS_DIR / f"{agent_key}.md"
        rel_path = str(agent_file.relative_to(ROOT)) if agent_file.exists() else f".claude/agents/{agent_key}.md"

        # Collect all errors/warnings for this agent
        agent_errors = [e for e in result.errors if agent_key in e.location or (e.file_path and agent_key in e.file_path)]
        agent_warnings = [w for w in result.warnings if agent_key in w.location or (w.file_path and agent_key in w.file_path)]

        checks: Dict[str, Any] = {}

        # FR-001: Bijection check
        bijection_errors = [e for e in agent_errors if e.error_type == "BIJECTION"]
        if bijection_errors:
            checks["FR-001"] = {
                "status": "fail",
                "message": bijection_errors[0].problem,
                "fix": bijection_errors[0].fix_action,
            }
        else:
            checks["FR-001"] = {"status": "pass", "message": "Registered in AGENTS.md"}

        # FR-002: Frontmatter check
        frontmatter_errors = [e for e in agent_errors if e.error_type == "FRONTMATTER"]
        frontmatter_warnings = [w for w in agent_warnings if w.error_type == "FRONTMATTER"]
        if frontmatter_errors:
            checks["FR-002"] = {
                "status": "fail",
                "message": frontmatter_errors[0].problem,
                "fix": frontmatter_errors[0].fix_action,
            }
        elif frontmatter_warnings:
            checks["FR-002"] = {
                "status": "warn",
                "message": frontmatter_warnings[0].problem,
                "fix": frontmatter_warnings[0].fix_action,
            }
        else:
            checks["FR-002"] = {"status": "pass", "message": "Frontmatter valid"}

        # Color check (part of FR-002b)
        color_errors = [e for e in agent_errors if e.error_type == "COLOR"]
        if color_errors:
            checks["FR-002b"] = {
                "status": "fail",
                "message": color_errors[0].problem,
                "fix": color_errors[0].fix_action,
            }
        else:
            checks["FR-002b"] = {"status": "pass", "message": "Color matches role family"}

        # Config check
        config_errors = [e for e in agent_errors if e.error_type == "CONFIG"]
        if config_errors:
            checks["FR-CONF"] = {
                "status": "fail",
                "message": config_errors[0].problem,
                "fix": config_errors[0].fix_action,
            }
        else:
            checks["FR-CONF"] = {"status": "pass", "message": "Config aligned"}

        # Determine overall status for this agent
        has_issues = any(c.get("status") == "fail" for c in checks.values())
        has_warnings = any(c.get("status") == "warn" for c in checks.values())

        agents_data[agent_key] = {
            "file": rel_path,
            "checks": checks,
            "has_issues": has_issues,
            "has_warnings": has_warnings,
            "issues": [e.to_dict() for e in agent_errors],
        }

    # Build flows section with per-flow check status
    flows_data: Dict[str, Any] = {}

    # Lazy import to support running validator in test repos without swarm/config/
    try:
        from swarm.config.flow_registry import get_flow_keys
        flow_keys = get_flow_keys()
    except ImportError:
        # Fallback: use canonical 7-flow keys if registry not available
        flow_keys = ["signal", "plan", "build", "review", "gate", "deploy", "wisdom"]

    for flow_id in flow_keys:
        flow_file = FLOW_SPECS_DIR / f"flow-{flow_id}.md"
        rel_path = str(flow_file.relative_to(ROOT)) if flow_file.exists() else f"swarm/flows/flow-{flow_id}.md"

        # Collect all errors for this flow
        flow_errors = [e for e in result.errors if flow_id in e.location or (e.file_path and flow_id in e.file_path)]

        checks = {}  # type: ignore[no-redef]

        # FR-003: Flow references check
        reference_errors = [e for e in flow_errors if e.error_type == "REFERENCE"]
        if reference_errors:
            checks["FR-003"] = {
                "status": "fail",
                "message": reference_errors[0].problem,
                "fix": reference_errors[0].fix_action,
            }
        else:
            checks["FR-003"] = {"status": "pass", "message": "All agent references valid"}

        # FR-005: RUN_BASE paths check
        runbase_errors = [e for e in flow_errors if e.error_type == "RUNBASE"]
        if runbase_errors:
            checks["FR-005"] = {
                "status": "fail",
                "message": runbase_errors[0].problem,
                "fix": runbase_errors[0].fix_action,
            }
        else:
            checks["FR-005"] = {"status": "pass", "message": "RUN_BASE paths correct"}

        # Flow-specific checks
        flow_check_errors = [e for e in flow_errors if e.error_type == "FLOW"]
        if flow_check_errors:
            checks["FR-FLOW"] = {
                "status": "fail",
                "message": flow_check_errors[0].problem,
                "fix": flow_check_errors[0].fix_action,
            }
        else:
            checks["FR-FLOW"] = {"status": "pass", "message": "Flow structure valid"}

        has_issues = any(c.get("status") == "fail" for c in checks.values())

        flows_data[flow_id] = {
            "file": rel_path,
            "checks": checks,
            "has_issues": has_issues,
            "issues": [e.to_dict() for e in flow_errors],
        }

    # Build steps section (for detailed step-level governance issues)
    steps_data: Dict[str, Any] = {}
    # Steps can be identified from flow config files
    if FLOWS_CONFIG_DIR.is_dir():
        for flow_file in sorted(FLOWS_CONFIG_DIR.glob("*.yaml")):
            flow_id = flow_file.stem
            flow_config = parse_flow_config(flow_file)
            for step in flow_config.get("steps", []):
                step_id = step.get("id", "")
                full_step_id = f"{flow_id}:{step_id}"

                # Check for step-specific issues (agentless steps, invalid agent refs)
                step_errors = [e for e in result.errors
                               if (e.error_type == "FLOW" and step_id in e.problem)]

                if step_errors:
                    steps_data[full_step_id] = {
                        "checks": {
                            "FR-FLOW": {
                                "status": "fail",
                                "message": step_errors[0].problem,
                                "fix": step_errors[0].fix_action,
                            }
                        },
                        "has_issues": True,
                        "issues": [e.to_dict() for e in step_errors],
                    }

    # Build skills section
    skills_data: Dict[str, Any] = {}
    skill_errors = [e for e in result.errors if e.error_type == "SKILL"]
    for err in skill_errors:
        # Extract skill name from error location or problem
        if "skill '" in err.problem:
            skill_name = err.problem.split("skill '")[1].split("'")[0]
        else:
            skill_name = err.location.replace("skill ", "").replace("'", "")

        skills_data[skill_name] = {
            "checks": {
                "FR-004": {
                    "status": "fail",
                    "message": err.problem,
                    "fix": err.fix_action,
                }
            },
            "has_issues": True,
        }

    # Calculate summary
    total_checks = len(result.errors) + len(result.warnings)
    agents_with_issues = [k for k, v in agents_data.items() if v.get("has_issues")]
    flows_with_issues = [k for k, v in flows_data.items() if v.get("has_issues")]
    steps_with_issues = [k for k, v in steps_data.items() if v.get("has_issues")]

    return {
        "version": "1.0.0",
        "timestamp": timestamp,
        "summary": {
            "total_checks": total_checks,
            "passed": total_checks - len(result.errors),
            "failed": len(result.errors),
            "warnings": len(result.warnings),
            "status": "PASS" if not result.has_errors() else "FAIL",
            "agents_with_issues": agents_with_issues,
            "flows_with_issues": flows_with_issues,
            "steps_with_issues": steps_with_issues,
        },
        "agents": agents_data,
        "flows": flows_data,
        "steps": steps_data,
        "skills": skills_data,
        "errors": [e.to_dict() for e in result.sorted_errors()],
        "warnings": [w.to_dict() for w in result.sorted_warnings()],
    }


def build_report_json(result: ValidationResult) -> Dict[str, Any]:
    """Build simplified FR-012 report JSON.

    This format is designed for machine consumption with a simpler schema
    than the detailed --json output.

    Args:
        result: The validation result containing errors and warnings

    Returns:
        Dictionary with simplified report data
    """
    checks = [
        "agent_bijection",
        "frontmatter",
        "flow_references",
        "skills",
        "runbase_paths",
    ]

    errors_list: list[dict[str, Any]] = []
    for error in result.sorted_errors():
        errors_list.append({
            "type": error.error_type,
            "file": error.file_path or error.location,
            "location": error.location,
            "line": error.line_number,
            "message": error.problem,
            "suggestions": [error.fix_action] if error.fix_action else [],
        })

    warnings_list: list[dict[str, Any]] = []
    for warning in result.sorted_warnings():
        warnings_list.append({
            "type": warning.error_type,
            "file": warning.file_path or warning.location,
            "location": warning.location,
            "line": warning.line_number,
            "message": warning.problem,
            "suggestions": [warning.fix_action] if warning.fix_action else [],
        })

    total_checks = len(result.errors) + len(result.warnings)
    passed = len(result.warnings)  # Warnings don't fail
    failed = len(result.errors)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "PASSED" if not result.has_errors() else "FAILED",
        "checks": checks,
        "total_checks": total_checks if total_checks > 0 else len(checks),
        "passed": passed,
        "failed": failed,
        "errors": errors_list,
        "warnings": warnings_list,
    }
