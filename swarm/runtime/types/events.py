"""
events.py - Specific event type definitions for Flow Studio.

This module defines the strict event contracts for the runtime event stream.
These classes are used to generate standardized RunEvent objects with
validated payloads, ensuring consistency between the runtime and the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .runs import RunEvent


@dataclass
class EventBase:
    """Base class for all specific event types."""

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        """Convert to generic RunEvent for persistence."""
        raise NotImplementedError


@dataclass
class StepStartEvent(EventBase):
    """Event emitted when a step execution begins."""

    step_id: str
    step_index: int
    inputs: Dict[str, Any] = field(default_factory=dict)

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="step_start",
            flow_key=flow_key,
            step_id=self.step_id,
            payload={
                "step_index": self.step_index,
                "inputs": self.inputs,
            },
        )


@dataclass
class StepEndEvent(EventBase):
    """Event emitted when a step execution completes."""

    step_id: str
    step_index: int
    status: str
    output: Any
    duration_ms: int

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="step_end",
            flow_key=flow_key,
            step_id=self.step_id,
            payload={
                "step_index": self.step_index,
                "status": self.status,
                "output": self.output,
                "duration_ms": self.duration_ms,
            },
        )


@dataclass
class FlowCompletedEvent(EventBase):
    """Event emitted when a flow completes."""

    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="flow_completed",
            flow_key=flow_key,
            step_id=None,
            payload={
                "status": self.status,
                "result": self.result,
                "error": self.error,
            },
        )


@dataclass
class FactsUpdatedEvent(EventBase):
    """Event emitted when shared context/facts are updated."""

    step_id: str
    facts: Dict[str, Any]
    delta: Optional[Dict[str, Any]] = None

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="facts_updated",
            flow_key=flow_key,
            step_id=self.step_id,
            payload={
                "facts": self.facts,
                "delta": self.delta,
            },
        )


@dataclass
class RunPausingEvent(EventBase):
    """Event emitted when a run pause is requested."""

    reason: str

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="run_pausing",
            flow_key=flow_key,
            step_id=None,
            payload={
                "reason": self.reason,
            },
        )


@dataclass
class RunPausedEvent(EventBase):
    """Event emitted when a run is effectively paused."""

    step_id: str
    reason: str

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="run_paused",
            flow_key=flow_key,
            step_id=self.step_id,
            payload={
                "reason": self.reason,
            },
        )


@dataclass
class RunResumedEvent(EventBase):
    """Event emitted when a run is resumed."""

    step_id: str

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="run_resumed",
            flow_key=flow_key,
            step_id=self.step_id,
            payload={},
        )


@dataclass
class RunStoppingEvent(EventBase):
    """Event emitted when a run stop is requested."""

    reason: str

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="run_stopping",
            flow_key=flow_key,
            step_id=None,
            payload={
                "reason": self.reason,
            },
        )


@dataclass
class RunStoppedEvent(EventBase):
    """Event emitted when a run is effectively stopped."""

    step_id: str
    reason: str

    def to_run_event(self, run_id: str, flow_key: str) -> RunEvent:
        return RunEvent(
            run_id=run_id,
            ts=datetime.now(timezone.utc),
            kind="run_stopped",
            flow_key=flow_key,
            step_id=self.step_id,
            payload={
                "reason": self.reason,
            },
        )
