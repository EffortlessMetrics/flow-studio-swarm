from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..deps import get_state
from ..state import FlowStudioState

try:
    from swarm.flowstudio import schema
except ImportError:
    schema = None

router = APIRouter()


@router.post(
    "/api/station/compile-preview",
    response_model=schema.CompilePreviewResponse if schema else None,
)
async def api_station_compile_preview(
    request: schema.CompilePreviewRequest if schema else None,
    state: FlowStudioState = Depends(get_state),
):
    if request is None:
        return JSONResponse({"error": "Request body required"}, status_code=400)

    try:
        from swarm.spec.compiler import SpecCompiler, COMPILER_VERSION
    except ImportError:
        return JSONResponse({"error": "SpecCompiler not available"}, status_code=503)

    run_base = state.repo_root / "swarm" / "runs" / (request.run_id or "default")

    try:
        compiler = SpecCompiler(repo_root=state.repo_root)
        plan = compiler.compile(
            flow_id=request.flow_id,
            step_id=request.step_id,
            context_pack=None,
            run_base=run_base,
            cwd=str(state.repo_root),
        )

        return {
            "flow_id": plan.flow_id,
            "step_id": plan.step_id,
            "station_id": plan.station_id,
            "system_prompt": plan.system_append,
            "user_prompt": plan.user_prompt,
            "sdk_options": {
                "model": plan.model,
                "tools": list(plan.allowed_tools),
                "permission_mode": plan.permission_mode,
                "max_turns": plan.max_turns,
                "sandbox_enabled": plan.sandbox_enabled,
                "cwd": plan.cwd,
            },
            "verification": {
                "required_artifacts": list(plan.verification.required_artifacts),
                "verification_commands": list(plan.verification.verification_commands),
            },
            "traceability": {
                "prompt_hash": plan.prompt_hash,
                "prompt_hash_v2": plan.prompt_hash_v2,
                "compiled_at": plan.compiled_at,
                "compiler_version": COMPILER_VERSION,
                "station_version": plan.station_version,
                "flow_version": plan.flow_version,
            },
        }
    except FileNotFoundError as exc:
        return JSONResponse(
            {
                "error": f"Spec not found: {str(exc)}",
                "hint": "Check that flow_id and step_id reference valid specs in swarm/specs/",
            },
            status_code=404,
        )
    except ValueError as exc:
        return JSONResponse(
            {
                "error": f"Invalid step: {str(exc)}",
                "hint": "Verify step_id matches a step in the specified flow",
            },
            status_code=400,
        )
    except Exception as exc:
        return JSONResponse({"error": f"Compilation failed: {str(exc)}"}, status_code=500)
