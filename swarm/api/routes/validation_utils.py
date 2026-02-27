from fastapi import HTTPException
from swarm.runtime.safe_paths import validate_path_component

def _validate_path_param(value: str, name: str) -> None:
    """Validate a path parameter using safe_paths logic.

    Raises:
        HTTPException(400): If validation fails.
    """
    try:
        validate_path_component(value, name)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_path_component",
                "message": str(e),
                "details": {name: value},
            },
        )
