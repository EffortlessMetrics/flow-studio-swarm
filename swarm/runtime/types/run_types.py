"""Run lifecycle and summary types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ._ids import BackendId, RunId, _generate_event_id
from ._time import _datetime_to_iso, _iso_to_datetime


class RunStatus(str, Enum):
    """Status of a run's execution lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    PARTIAL = "partial"
    STOPPING = "stopping"
    STOPPED = "stopped"
    PAUSING = "pausing"
    PAUSED = "paused"


class SDLCStatus(str, Enum):
    """Status reflecting SDLC health/quality outcome."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"
    PARTIAL = "partial"


@dataclass
class RunSpec:
    """Specification for starting a new run."""

    flow_keys: List[str]
    profile_id: Optional[str] = None
    backend: BackendId = "claude-harness"
    initiator: str = "cli"
    params: Dict[str, Any] = field(default_factory=dict)
    no_human_mid_flow: bool = False


@dataclass
class RunSummary:
    """Summary of a run's current state."""

    id: RunId
    spec: RunSpec
    status: RunStatus
    sdlc_status: SDLCStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    is_exemplar: bool = False
    tags: List[str] = field(default_factory=list)
    title: Optional[str] = None
    path: Optional[str] = None
    description: Optional[str] = None


@dataclass
class RunEvent:
    """A single event in a run's timeline."""

    run_id: RunId
    ts: datetime
    kind: str
    flow_key: str
    event_id: str = field(default_factory=_generate_event_id)
    seq: int = 0
    step_id: Optional[str] = None
    agent_key: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendCapabilities:
    """Describes what a backend can do."""

    id: BackendId
    label: str
    supports_streaming: bool = False
    supports_events: bool = True
    supports_cancel: bool = False
    supports_replay: bool = False


def run_spec_to_dict(spec: RunSpec) -> Dict[str, Any]:
    """Convert RunSpec to a dictionary for serialization."""
    return {
        "flow_keys": list(spec.flow_keys),
        "profile_id": spec.profile_id,
        "backend": spec.backend,
        "initiator": spec.initiator,
        "params": dict(spec.params),
        "no_human_mid_flow": spec.no_human_mid_flow,
    }


def run_spec_from_dict(data: Dict[str, Any]) -> RunSpec:
    """Parse RunSpec from a dictionary."""
    return RunSpec(
        flow_keys=list(data.get("flow_keys", [])),
        profile_id=data.get("profile_id"),
        backend=data.get("backend", "claude-harness"),
        initiator=data.get("initiator", "unknown"),
        params=dict(data.get("params", {})),
        no_human_mid_flow=data.get("no_human_mid_flow", False),
    )


def run_summary_to_dict(summary: RunSummary) -> Dict[str, Any]:
    """Convert RunSummary to a dictionary for serialization."""
    return {
        "id": summary.id,
        "spec": run_spec_to_dict(summary.spec),
        "status": summary.status.value,
        "sdlc_status": summary.sdlc_status.value,
        "created_at": _datetime_to_iso(summary.created_at),
        "updated_at": _datetime_to_iso(summary.updated_at),
        "started_at": _datetime_to_iso(summary.started_at),
        "completed_at": _datetime_to_iso(summary.completed_at),
        "error": summary.error,
        "artifacts": dict(summary.artifacts),
        "is_exemplar": summary.is_exemplar,
        "tags": list(summary.tags),
        "title": summary.title,
        "path": summary.path,
        "description": summary.description,
    }


def run_summary_from_dict(data: Dict[str, Any]) -> RunSummary:
    """Parse RunSummary from a dictionary."""
    now = datetime.now(timezone.utc)
    return RunSummary(
        id=data.get("id", ""),
        spec=run_spec_from_dict(data.get("spec", {})),
        status=RunStatus(data.get("status", "pending")),
        sdlc_status=SDLCStatus(data.get("sdlc_status", "unknown")),
        created_at=_iso_to_datetime(data.get("created_at")) or now,
        updated_at=_iso_to_datetime(data.get("updated_at")) or now,
        started_at=_iso_to_datetime(data.get("started_at")),
        completed_at=_iso_to_datetime(data.get("completed_at")),
        error=data.get("error"),
        artifacts=dict(data.get("artifacts", {})),
        is_exemplar=data.get("is_exemplar", False),
        tags=list(data.get("tags", [])),
        title=data.get("title"),
        path=data.get("path"),
        description=data.get("description"),
    )


def run_event_to_dict(event: RunEvent) -> Dict[str, Any]:
    """Convert RunEvent to a dictionary for serialization."""
    return {
        "event_id": event.event_id,
        "seq": event.seq,
        "run_id": event.run_id,
        "ts": _datetime_to_iso(event.ts),
        "kind": event.kind,
        "flow_key": event.flow_key,
        "step_id": event.step_id,
        "agent_key": event.agent_key,
        "payload": dict(event.payload),
    }


def run_event_from_dict(data: Dict[str, Any]) -> RunEvent:
    """Parse RunEvent from a dictionary."""
    return RunEvent(
        run_id=data.get("run_id", ""),
        ts=_iso_to_datetime(data.get("ts")) or datetime.now(timezone.utc),
        kind=data.get("kind", "unknown"),
        flow_key=data.get("flow_key", ""),
        event_id=data.get("event_id", _generate_event_id()),
        seq=data.get("seq", 0),
        step_id=data.get("step_id"),
        agent_key=data.get("agent_key"),
        payload=dict(data.get("payload", {})),
    )
