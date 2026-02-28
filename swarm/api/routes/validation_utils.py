"""
Validation utilities for API routes.
"""

from fastapi import HTTPException
from swarm.runtime.safe_paths import validate_path_component

def _validate_path_param(value: str, name: str) -> str:
    """Validate a path parameter to prevent path traversal.

    Args:
        value: The path parameter value to validate.
        name: The name of the parameter for error messages.

    Returns:
        The validated value.

    Raises:
        HTTPException: 400 Bad Request if validation fails.
    """
    try:
        return validate_path_component(value, name)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_path_parameter",
                "message": str(e),
                "details": {name: value}
            }
        )
