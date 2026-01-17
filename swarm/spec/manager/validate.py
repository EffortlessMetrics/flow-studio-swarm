from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from .models import ValidationError


def check_jsonschema(logger: logging.Logger) -> bool:
    """Check if jsonschema is available."""
    try:
        import jsonschema  # noqa: F401

        return True
    except ImportError:
        logger.warning("jsonschema not installed - schema validation will be skipped")
        return False


def validate_spec(
    schema_loader: Callable[[str], Optional[Dict[str, Any]]],
    spec_type: str,
    data: Dict[str, Any],
    jsonschema_available: bool,
    logger: logging.Logger,
) -> List[ValidationError]:
    """Validate spec data against its JSON schema."""
    errors: List[ValidationError] = []

    if not jsonschema_available:
        logger.debug("Schema validation skipped (jsonschema not available)")
        return errors

    schema = schema_loader(spec_type)
    if not schema:
        errors.append(
            ValidationError(
                path="",
                message=f"Schema '{spec_type}' not found",
            )
        )
        return errors

    try:
        import jsonschema  # noqa: F401
        from jsonschema import Draft7Validator

        validator = Draft7Validator(schema)
        for error in validator.iter_errors(data):
            path = ".".join(str(p) for p in error.absolute_path) or "root"
            schema_path = ".".join(str(p) for p in error.schema_path)
            errors.append(
                ValidationError(
                    path=path,
                    message=error.message,
                    schema_path=schema_path,
                    value=error.instance,
                )
            )
    except Exception as e:
        errors.append(
            ValidationError(
                path="",
                message=f"Validation error: {e}",
            )
        )

    return errors
