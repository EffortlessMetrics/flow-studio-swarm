from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .models import ValidationError


class SpecError(Exception):
    """Base exception for spec-related errors."""

    pass


class SpecNotFoundError(SpecError):
    """Raised when a requested spec file does not exist."""

    def __init__(self, spec_type: str, spec_id: str, path: Optional[Path] = None):
        self.spec_type = spec_type
        self.spec_id = spec_id
        self.path = path
        msg = f"{spec_type} '{spec_id}' not found"
        if path:
            msg += f" at {path}"
        super().__init__(msg)


class SpecValidationError(SpecError):
    """Raised when spec data fails schema validation."""

    def __init__(self, spec_type: str, errors: List["ValidationError"]):
        self.spec_type = spec_type
        self.errors = errors
        error_msgs = "; ".join(str(e) for e in errors)
        super().__init__(f"{spec_type} validation failed: {error_msgs}")


class ConcurrencyError(SpecError):
    """Raised when ETag mismatch indicates concurrent modification."""

    def __init__(self, spec_type: str, spec_id: str, expected_etag: str, actual_etag: str):
        self.spec_type = spec_type
        self.spec_id = spec_id
        self.expected_etag = expected_etag
        self.actual_etag = actual_etag
        super().__init__(
            f"{spec_type} '{spec_id}' was modified by another process. "
            f"Expected ETag: {expected_etag}, Actual: {actual_etag}"
        )
