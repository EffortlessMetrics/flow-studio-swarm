from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def compile_to_prompt_plan(
    repo_root: Path,
    flow_id: str,
    step_id: Optional[str] = None,
    run_base: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compile a flow to a prompt plan."""
    from ..compiler import SpecCompiler
    from ..loader import load_flow

    # Load flow to get step information
    flow = load_flow(flow_id, repo_root)

    # Default to first step
    if step_id is None and flow.steps:
        step_id = flow.steps[0].id

    if step_id is None:
        raise ValueError(f"Flow {flow_id} has no steps")

    # Default run base
    if run_base is None:
        run_base = repo_root / "swarm" / "runs" / "default"

    # Compile
    compiler = SpecCompiler(repo_root)
    plan = compiler.compile(
        flow_id=flow_id,
        step_id=step_id,
        context_pack=None,  # No context pack for basic compilation
        run_base=run_base,
    )

    # Convert dataclass to dict for return
    # PromptPlan is a frozen dataclass, convert manually
    return {
        "station_id": plan.station_id,
        "station_version": plan.station_version,
        "flow_id": plan.flow_id,
        "flow_version": plan.flow_version,
        "step_id": plan.step_id,
        "prompt_hash": plan.prompt_hash,
        "prompt_hash_v2": plan.prompt_hash_v2,
        "model": plan.model,
        "permission_mode": plan.permission_mode,
        "allowed_tools": list(plan.allowed_tools),
        "max_turns": plan.max_turns,
        "sandbox_enabled": plan.sandbox_enabled,
        "cwd": plan.cwd,
        "system_append": plan.system_append,
        "user_prompt": plan.user_prompt,
        "compiled_at": plan.compiled_at,
        "context_pack_size": plan.context_pack_size,
        "flow_key": plan.flow_key,
        "verification": {
            "required_artifacts": list(plan.verification.required_artifacts),
            "verification_commands": list(plan.verification.verification_commands),
        },
        "handoff": {
            "path": plan.handoff.path,
            "required_fields": list(plan.handoff.required_fields),
        },
    }
