import logging

from fastapi import HTTPException

from swarm.runtime.safe_paths import validate_path_component

logger = logging.getLogger(__name__)


def _validate_path_param(value: str, name: str = "path component") -> str:
    """Validate a path parameter to prevent path traversal.

    Args:
        value: The string to validate.
        name: Name of the parameter for error messages.

    Returns:
        The validated string.

    Raises:
        HTTPException: If the string contains invalid characters or traversal sequences.
    """
    try:
        return validate_path_component(value, name)
    except ValueError as e:
        logger.warning("Path validation failed for %s: %s", name, e)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_path",
                "message": str(e),
                "details": {name: value},
            },
        )
