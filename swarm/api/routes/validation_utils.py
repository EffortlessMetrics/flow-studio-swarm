"""
validation_utils.py - Reusable parameter validation for API routes.

Standardizes the translation of application-level validation errors
(like path traversal blocks) into appropriate HTTP responses.
"""

from fastapi import HTTPException

from swarm.runtime.safe_paths import validate_path_component


def _validate_path_param(value: str, name: str = "path_component") -> str:
    """Validate a path parameter to prevent path traversal.

    Wraps the core safe_paths validation and converts ValueErrors
    into consistent HTTP 400 Bad Request exceptions.

    Args:
        value: The string to validate.
        name: Name of the variable for error messages.

    Returns:
        The validated component (same as input).

    Raises:
        HTTPException: 400 status if validation fails.
    """
    try:
        return validate_path_component(value, name)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_path_component",
                "message": str(e),
                "details": {name: value},
            },
        )
