"""
validation_utils.py - Reusable validation helpers for API routes.
"""

from fastapi import HTTPException

from swarm.runtime.safe_paths import validate_path_component


def _validate_path_param(param_value: str, param_name: str) -> str:
    """Validate a path parameter and raise an HTTPException (400) if invalid.

    Args:
        param_value: The value of the path parameter.
        param_name: The name of the parameter for error messages.

    Returns:
        The validated parameter value.

    Raises:
        HTTPException: With status 400 if validation fails.
    """
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
