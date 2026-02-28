from fastapi import HTTPException
from swarm.runtime.safe_paths import validate_path_component

def _validate_path_param(param_value: str, param_name: str) -> str:
    """Validate a path parameter to prevent path traversal.

    Args:
        param_value: The value to validate.
        param_name: The name of the parameter for error messages.

    Returns:
        The validated parameter.

    Raises:
        HTTPException: 400 Bad Request if validation fails.
    """
    try:
        return validate_path_component(param_value, param_name)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_path_parameter",
                "message": str(e),
                "details": {"parameter": param_name, "value": param_value},
            },
        )
