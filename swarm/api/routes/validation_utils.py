"""
validation_utils.py - Reusable validation helpers for API routes.
"""

from fastapi import HTTPException
from swarm.runtime.safe_paths import validate_path_component

def _validate_path_param(value: str, name: str) -> str:
    """Validate a path parameter and raise 400 HTTPException on failure.

    Args:
        value: The path parameter value.
        name: The name of the parameter for the error message.

    Returns:
        The validated value.

    Raises:
        HTTPException: With status 400 if validation fails.
    """
    try:
        return validate_path_component(value, name)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_path_parameter",
                "message": str(e),
                "details": {"parameter": name, "value": value},
            },
        )
