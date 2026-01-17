from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ..services.model_policy import get_model_policy_matrix, preview_model_policy

try:
    from swarm.flowstudio import schema
except ImportError:
    schema = None

router = APIRouter()


@router.get(
    "/api/model-policy/preview",
    response_model=schema.ModelPolicyPreviewResponse if schema else None,
)
async def api_model_policy_preview(
    category: str = Query(..., description="Station category (e.g., implementation, critic, shaping)"),
    model: str = Query("inherit", description="Model value to resolve (inherit, haiku, sonnet, opus)"),
):
    try:
        return preview_model_policy(category, model)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except ImportError:
        return JSONResponse({"error": "Model registry not available"}, status_code=503)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to preview model policy: {str(exc)}"},
            status_code=500,
        )


@router.get(
    "/api/model-policy/matrix",
    response_model=schema.ModelPolicyMatrixResponse if schema else None,
)
async def api_model_policy_matrix():
    try:
        return get_model_policy_matrix()
    except ImportError:
        return JSONResponse({"error": "Model registry not available"}, status_code=503)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to get model policy matrix: {str(exc)}"},
            status_code=500,
        )
