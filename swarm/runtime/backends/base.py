"""base - Abstract RunBackend interface.

Defines the contract every run execution backend implements. Concrete
backends live in sibling modules and are wired together in registry.py.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from ..types import (
    BackendCapabilities,
    BackendId,
    RunEvent,
    RunId,
    RunSpec,
    RunSummary,
)

logger = logging.getLogger(__name__)



class RunBackend(ABC):
    """Abstract base class for run execution backends.

    Backends are responsible for:
    - Starting runs (non-blocking, returns immediately)
    - Tracking run status
    - Providing run summaries and events
    - Optionally supporting cancellation
    """

    @property
    @abstractmethod
    def id(self) -> BackendId:
        """Unique identifier for this backend."""
        ...

    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        """Return what this backend supports."""
        ...

    @abstractmethod
    def start(self, spec: RunSpec) -> RunId:
        """Start a run. Returns immediately with run ID."""
        ...

    @abstractmethod
    def get_summary(self, run_id: RunId) -> Optional[RunSummary]:
        """Get current summary for a run."""
        ...

    @abstractmethod
    def list_summaries(self) -> List[RunSummary]:
        """List all known runs."""
        ...

    @abstractmethod
    def get_events(self, run_id: RunId) -> List[RunEvent]:
        """Get all events for a run."""
        ...

    def cancel(self, run_id: RunId) -> bool:
        """Cancel a running run. Returns True if cancelled."""
        return False  # Default: not supported
