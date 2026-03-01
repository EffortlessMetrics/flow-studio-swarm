from fastapi import HTTPException
from swarm.runtime.safe_paths import validate_path_component

def _validate_path_param(param_value: str, param_name: str) -> str:
    """Validate a path parameter and raise an appropriate HTTPException if invalid."""
    try:
        return validate_path_component(param_value, param_name)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_path_parameter",
                "message": str(e),
                "details": {param_name: param_value},
            },
        )
