from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

try:
    from swarm.config.profile_registry import get_current_profile, list_profiles
except ImportError:
    get_current_profile = None
    list_profiles = None

router = APIRouter()


@router.get("/api/profile")
async def api_current_profile():
    if get_current_profile is None:
        return JSONResponse(
            {"error": "Profile registry not available", "profile": None},
            status_code=503,
        )

    try:
        current = get_current_profile()
        if current is None:
            return {
                "profile": None,
                "message": "No profile currently loaded. Use 'make profile-load' to apply a profile.",
            }

        return {
            "profile": {
                "id": current.id,
                "label": current.label,
                "loaded_at": current.loaded_at,
                "source_branch": current.source_branch,
            }
        }
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to get current profile: {str(exc)}", "profile": None},
            status_code=500,
        )


@router.get("/api/profiles")
async def api_list_profiles():
    if list_profiles is None:
        return JSONResponse(
            {"error": "Profile registry not available", "profiles": []},
            status_code=503,
        )

    try:
        profiles = list_profiles()
        return {
            "profiles": [
                {
                    "id": p.id,
                    "label": p.label,
                    "description": p.description,
                }
                for p in profiles
            ]
        }
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to list profiles: {str(exc)}", "profiles": []},
            status_code=500,
        )
