"""Telemetry data structures for the Claude SDK integration.

This module provides:
- TelemetryData dataclass for tracking session phase metrics
- Methods for recording tool calls and finalizing telemetry

These are SDK-free modules (no SDK calls involved).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TelemetryData:
    """Telemetry data collected during a session phase.

    Attributes:
        phase: The phase name (work, finalize, route).
        start_time: When the phase started (ISO timestamp).
        end_time: When the phase ended (ISO timestamp).
        duration_ms: Total duration in milliseconds.
        tool_calls: Number of tool calls made.
        tool_timings: Dict of tool_name -> list of call durations (ms).
        prompt_tokens: Input tokens used.
        completion_tokens: Output tokens used.
        model: Model used for this phase.
        errors: List of errors encountered.
    """

    phase: str
    start_time: str
    end_time: str = ""
    duration_ms: int = 0
    tool_calls: int = 0
    tool_timings: Dict[str, List[float]] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    errors: List[str] = field(default_factory=list)

    def record_tool_call(self, tool_name: str, duration_ms: float) -> None:
        """Record a tool call timing."""
        self.tool_calls += 1
        if tool_name not in self.tool_timings:
            self.tool_timings[tool_name] = []
        self.tool_timings[tool_name].append(duration_ms)

    def finalize(self, end_time: Optional[datetime] = None) -> None:
        """Finalize telemetry with end time and duration."""
        end = end_time or datetime.now(timezone.utc)
        self.end_time = end.isoformat() + "Z"
        # Parse start_time to calculate duration
        try:
            start_str = self.start_time.rstrip("Z")
            start = datetime.fromisoformat(start_str)
            # Make start timezone-aware if it isn't
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            self.duration_ms = int((end - start).total_seconds() * 1000)
        except (ValueError, TypeError):
            pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "phase": self.phase,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tool_calls": self.tool_calls,
            "tool_timings": self.tool_timings,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "model": self.model,
            "errors": self.errors,
        }
