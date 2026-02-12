from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .events import normalize_event_kind, parse_event_ts

logger = logging.getLogger(__name__)

# Thread-local flag to indicate we're inside ingest_events()
# When True, record_* calls are allowed even in projection-only mode
_ingestion_context = threading.local()


def _is_in_ingestion_context() -> bool:
    """Check if we're currently inside ingest_events()."""
    return getattr(_ingestion_context, "active", False)


class StatsDBIngestionMixin:
    def _insert_raw_event(self, event: Dict[str, Any]) -> bool:
        """Insert raw event if not already present. Returns True if inserted."""
        try:
            # Use RETURNING to detect if insert happened (empty result = conflict/no insert)
            result = self.connection.execute(
                """
                INSERT INTO events (event_id, seq, run_id, ts, kind, flow_key, step_id, agent_key, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id
            """,
                [
                    event.get("event_id"),
                    event.get("seq", 0),
                    event["run_id"],
                    event["ts"],
                    event["kind"],
                    event["flow_key"],
                    event.get("step_id"),
                    event.get("agent_key"),
                    json.dumps(event.get("payload", {})),
                ],
            )
            return len(result.fetchall()) > 0
        except Exception as e:
            logger.warning(f"Failed to insert event {event.get('event_id')}: {e}")
            return False

    def get_ingestion_offset(self, run_id: str) -> Tuple[int, int]:
        """Get (byte_offset, last_seq) for incremental ingestion."""
        if self.connection is None:
            return (0, 0)

        with self._lock:
            result = self.connection.execute(
                "SELECT last_offset, last_seq FROM ingestion_state WHERE run_id = ?", [run_id]
            ).fetchone()
            return (result[0], result[1]) if result else (0, 0)

    def set_ingestion_offset(self, run_id: str, offset: int, seq: int) -> None:
        """Update ingestion offset after successful tail."""
        if self.connection is None:
            return

        with self._lock:
            self.connection.execute(
                """
                INSERT INTO ingestion_state (run_id, last_offset, last_seq, updated_at)
                VALUES (?, ?, ?, now())
                ON CONFLICT (run_id) DO UPDATE SET
                    last_offset = excluded.last_offset,
                    last_seq = excluded.last_seq,
                    updated_at = excluded.updated_at
            """,
                [run_id, offset, seq],
            )

    def record_run_start(
        self,
        run_id: str,
        flow_keys: List[str],
        profile_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ts: Optional[datetime] = None,
    ):
        """Record the start of a new run.

        Note: In projection-only mode, this is a no-op. Use event emission
        + ingest_events() instead.

        Args:
            ts: Optional timestamp from event. If None, uses current time.
                For replay/rebuild, always pass the event timestamp.
        """
        if self.connection is None:
            return
        if not self._projection_guard("record_run_start"):
            return

        started_at = ts if ts is not None else datetime.now(timezone.utc)
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, flow_keys, profile_id, engine_id, started_at, status, metadata)
                VALUES (?, ?, ?, ?, ?, 'running', ?)
                ON CONFLICT (run_id) DO UPDATE SET
                    flow_keys = EXCLUDED.flow_keys,
                    started_at = EXCLUDED.started_at,
                    status = 'running'
                """,
                [run_id, flow_keys, profile_id, engine_id, started_at, json.dumps(metadata or {})],
            )

    def record_run_end(
        self,
        run_id: str,
        status: str,
        total_steps: int,
        completed_steps: int,
        total_tokens: int,
        total_duration_ms: int,
        ts: Optional[datetime] = None,
    ):
        """Record the completion of a run.

        Note: In projection-only mode, this is a no-op. Use event emission
        + ingest_events() instead.

        Args:
            ts: Optional timestamp from event. If None, uses current time.
        """
        if self.connection is None:
            return
        if not self._projection_guard("record_run_end"):
            return

        completed_at = ts if ts is not None else datetime.now(timezone.utc)
        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE runs SET
                    completed_at = ?,
                    status = ?,
                    total_steps = ?,
                    completed_steps = ?,
                    total_tokens = ?,
                    total_duration_ms = ?
                WHERE run_id = ?
                """,
                [
                    completed_at,
                    status,
                    total_steps,
                    completed_steps,
                    total_tokens,
                    total_duration_ms,
                    run_id,
                ],
            )

    def record_step_start(
        self,
        run_id: str,
        flow_key: str,
        step_id: str,
        step_index: int,
        agent_key: Optional[str] = None,
        ts: Optional[datetime] = None,
    ):
        """Record the start of a step execution.

        Note: In projection-only mode, this is a no-op. Use event emission
        + ingest_events() instead.

        Args:
            ts: Optional timestamp from event. If None, uses current time.
        """
        if self.connection is None:
            return
        if not self._projection_guard("record_step_start"):
            return

        started_at = ts if ts is not None else datetime.now(timezone.utc)
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO steps (run_id, flow_key, step_id, step_index, agent_key, started_at, status)
                VALUES (?, ?, ?, ?, ?, ?, 'running')
                """,
                [run_id, flow_key, step_id, step_index, agent_key, started_at],
            )

    def record_step_end(
        self,
        run_id: str,
        flow_key: str,
        step_id: str,
        status: str,
        duration_ms: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        handoff_status: Optional[str] = None,
        routing_decision: Optional[str] = None,
        routing_next_step: Optional[str] = None,
        routing_confidence: Optional[float] = None,
        error_message: Optional[str] = None,
        ts: Optional[datetime] = None,
    ):
        """Record the completion of a step execution.

        Note: In projection-only mode, this is a no-op. Use event emission
        + ingest_events() instead.

        Args:
            ts: Optional timestamp from event. If None, uses current time.
        """
        if self.connection is None:
            return
        if not self._projection_guard("record_step_end"):
            return

        completed_at = ts if ts is not None else datetime.now(timezone.utc)
        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE steps SET
                    completed_at = ?,
                    status = ?,
                    duration_ms = ?,
                    prompt_tokens = ?,
                    completion_tokens = ?,
                    total_tokens = ?,
                    handoff_status = ?,
                    routing_decision = ?,
                    routing_next_step = ?,
                    routing_confidence = ?,
                    error_message = ?
                WHERE run_id = ? AND flow_key = ? AND step_id = ? AND status = 'running'
                """,
                [
                    completed_at,
                    status,
                    duration_ms,
                    prompt_tokens,
                    completion_tokens,
                    prompt_tokens + completion_tokens,
                    handoff_status,
                    routing_decision,
                    routing_next_step,
                    routing_confidence,
                    error_message,
                    run_id,
                    flow_key,
                    step_id,
                ],
            )

    def record_tool_call(
        self,
        run_id: str,
        step_id: str,
        tool_name: str,
        phase: str = "work",
        duration_ms: int = 0,
        success: bool = True,
        target_path: Optional[str] = None,
        diff_lines_added: Optional[int] = None,
        diff_lines_removed: Optional[int] = None,
        exit_code: Optional[int] = None,
        error_message: Optional[str] = None,
        ts: Optional[datetime] = None,
    ):
        """Record a tool call.

        Note: In projection-only mode, this is a no-op. Use event emission
        + ingest_events() instead.

        Args:
            ts: Optional timestamp from event. If None, uses current time.
        """
        if self.connection is None:
            return
        if not self._projection_guard("record_tool_call"):
            return

        tool_ts = ts if ts is not None else datetime.now(timezone.utc)
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO tool_calls (
                    run_id, step_id, tool_name, phase, started_at, completed_at,
                    duration_ms, success, target_path, diff_lines_added, diff_lines_removed,
                    exit_code, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    step_id,
                    tool_name,
                    phase,
                    tool_ts,
                    tool_ts,
                    duration_ms,
                    success,
                    target_path,
                    diff_lines_added,
                    diff_lines_removed,
                    exit_code,
                    error_message,
                ],
            )

    def record_file_change(
        self,
        run_id: str,
        step_id: str,
        file_path: str,
        change_type: str,
        lines_added: int = 0,
        lines_removed: int = 0,
        ts: Optional[datetime] = None,
    ):
        """Record a file change.

        Note: In projection-only mode, this is a no-op. Use event emission
        + ingest_events() instead.

        Args:
            ts: Optional timestamp from event. If None, uses current time.
        """
        if self.connection is None:
            return
        if not self._projection_guard("record_file_change"):
            return

        change_ts = ts if ts is not None else datetime.now(timezone.utc)
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO file_changes (run_id, step_id, file_path, change_type, lines_added, lines_removed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (run_id, step_id, file_path) DO UPDATE SET
                    change_type = EXCLUDED.change_type,
                    lines_added = file_changes.lines_added + EXCLUDED.lines_added,
                    lines_removed = file_changes.lines_removed + EXCLUDED.lines_removed
                """,
                [run_id, step_id, file_path, change_type, lines_added, lines_removed, change_ts],
            )

    def record_routing_decision(
        self,
        run_id: str,
        step_seq: int,
        flow_id: str,
        station_id: str,
        decision: str,
        routing_mode: Optional[str] = None,
        routing_source: Optional[str] = None,
        chosen_candidate_id: Optional[str] = None,
        candidate_count: int = 0,
        target_node: Optional[str] = None,
        terminate: bool = False,
        needs_human: bool = False,
        explanation: Optional[Dict[str, Any]] = None,
        ts: Optional[datetime] = None,
    ):
        """Record a routing decision.

        Captures the routing decision made after a step execution for
        audit trail and UI visualization.

        Note: In projection-only mode, this is a no-op. Use event emission
        + ingest_events() instead.

        Args:
            run_id: The run this decision belongs to.
            step_seq: Sequence number of the step within the run.
            flow_id: The flow key (signal, plan, build, etc.).
            station_id: The step/node that made the decision.
            decision: The routing decision (advance/loop/repeat/detour/terminate/escalate).
            routing_mode: How the decision was made (deterministic, llm_tiebreak, etc.).
            routing_source: Source of the routing (navigator/fast_path/deterministic_fallback).
            chosen_candidate_id: The selected edge ID.
            candidate_count: Number of candidate edges evaluated.
            target_node: The next node to execute (None for terminate).
            terminate: Whether the flow should terminate.
            needs_human: Whether human review is recommended.
            explanation: Full structured explanation for audit trail.
            ts: Optional timestamp from event. If None, uses current time.
        """
        if self.connection is None:
            return
        if not self._projection_guard("record_routing_decision"):
            return

        decision_ts = ts if ts is not None else datetime.now(timezone.utc)
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO routing_decisions (
                    run_id, step_seq, flow_id, station_id, routing_mode, routing_source,
                    chosen_candidate_id, candidate_count, decision, target_node,
                    timestamp, terminate, needs_human, explanation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (run_id, step_seq, station_id, timestamp) DO UPDATE SET
                    routing_mode = EXCLUDED.routing_mode,
                    routing_source = EXCLUDED.routing_source,
                    chosen_candidate_id = EXCLUDED.chosen_candidate_id,
                    candidate_count = EXCLUDED.candidate_count,
                    decision = EXCLUDED.decision,
                    target_node = EXCLUDED.target_node,
                    terminate = EXCLUDED.terminate,
                    needs_human = EXCLUDED.needs_human,
                    explanation = EXCLUDED.explanation
                """,
                [
                    run_id,
                    step_seq,
                    flow_id,
                    station_id,
                    routing_mode,
                    routing_source,
                    chosen_candidate_id,
                    candidate_count,
                    decision,
                    target_node,
                    decision_ts,
                    terminate,
                    needs_human,
                    json.dumps(explanation) if explanation else None,
                ],
            )

    def ingest_fact(
        self,
        run_id: str,
        step_id: str,
        flow_key: str,
        marker_type: str,
        marker_id: str,
        fact_type: str,
        content: str,
        agent_key: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        evidence: Optional[str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ts: Optional[datetime] = None,
    ) -> Optional[str]:
        """Ingest a fact (inventory marker) into the facts table.

        Facts represent structured information extracted from agent outputs
        using markers like REQ_001, SOL_002, TRC_003, ASM_001, DEC_001.

        Note: In projection-only mode, this is a no-op unless called from
        within ingest_events() context.

        Args:
            run_id: The run this fact belongs to.
            step_id: The step that produced this fact.
            flow_key: The flow (signal, plan, build, gate, deploy, wisdom).
            marker_type: The marker prefix (REQ, SOL, TRC, ASM, DEC, etc.).
            marker_id: The full marker ID (e.g., REQ_001).
            fact_type: Human-readable type (requirement, solution, trace, etc.).
            content: The fact content/description.
            agent_key: The agent that produced this fact.
            priority: Priority level (MUST, SHOULD, NICE_TO_HAVE).
            status: Fact status (verified, unverified, deprecated).
            evidence: Supporting evidence or references.
            created_at: When the fact was originally created.
            metadata: Additional structured metadata.
            ts: Timestamp for extraction (defaults to now).

        Returns:
            The generated fact_id if successful, None otherwise.
        """
        if self.connection is None:
            return None
        if not self._projection_guard("ingest_fact"):
            return None

        import uuid

        fact_id = f"fact_{uuid.uuid4().hex[:12]}"
        extracted_at = ts if ts is not None else datetime.now(timezone.utc)

        with self._transaction() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO facts (
                        fact_id, run_id, step_id, flow_key, agent_key,
                        marker_type, marker_id, fact_type, content,
                        priority, status, evidence, created_at, extracted_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (run_id, step_id, marker_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        priority = EXCLUDED.priority,
                        status = EXCLUDED.status,
                        evidence = EXCLUDED.evidence,
                        metadata = EXCLUDED.metadata,
                        extracted_at = EXCLUDED.extracted_at
                    """,
                    [
                        fact_id,
                        run_id,
                        step_id,
                        flow_key,
                        agent_key,
                        marker_type,
                        marker_id,
                        fact_type,
                        content,
                        priority,
                        status,
                        evidence,
                        created_at,
                        extracted_at,
                        json.dumps(metadata or {}),
                    ],
                )
                return fact_id
            except Exception as e:
                logger.warning("Failed to ingest fact %s: %s", marker_id, e)
                return None

    def ingest_events(self, events: List[Dict[str, Any]], run_id: str) -> int:
        """Batch ingest events from events.jsonl format (idempotent).

        This is the primary interface for the event sink pattern.
        First inserts raw events into the events table (dedup by event_id),
        then updates projections (runs, steps, tool_calls, file_changes).

        This method sets the ingestion context flag, allowing internal
        record_* calls to proceed even in projection-only mode.

        Args:
            events: List of event dicts (from events.jsonl).
            run_id: The run ID these events belong to.

        Returns:
            Number of newly ingested events (events that were not already present).
        """
        if self.connection is None:
            return 0

        # Set ingestion context to allow record_* calls
        _ingestion_context.active = True
        try:
            # Optimize: use a single transaction for the entire batch
            # This significantly reduces I/O overhead compared to per-row commits
            with self._lock:
                self.connection.execute("BEGIN TRANSACTION")
                try:
                    result = self._ingest_events_internal(events, run_id)
                    self.connection.execute("COMMIT")
                    return result
                except Exception:
                    self.connection.execute("ROLLBACK")
                    raise
        finally:
            _ingestion_context.active = False

    def _ingest_events_internal(self, events: List[Dict[str, Any]], run_id: str) -> int:
        """Internal implementation of ingest_events."""
        newly_ingested = 0

        for event in events:
            # Ensure run_id is set on the event for raw storage
            event_with_run = {**event, "run_id": run_id}

            # Insert raw event first (idempotent - skips if event_id exists)
            if not self._insert_raw_event(event_with_run):
                # Event already exists, skip projection updates
                continue

            newly_ingested += 1

            # Parse event timestamp - CRITICAL: use event's ts, not "now"
            # This ensures replays and rebuilds produce identical projections
            event_ts = parse_event_ts(event.get("ts"))

            # Normalize event kind to canonical form (handles legacy aliases)
            raw_kind = event.get("kind", "")
            kind = normalize_event_kind(raw_kind)
            payload = event.get("payload", {})
            step_id = event.get("step_id", "")
            flow_key = event.get("flow_key", "")

            if kind == "step_start":
                self.record_step_start(
                    run_id=run_id,
                    flow_key=flow_key,
                    step_id=step_id,
                    step_index=payload.get("step_index", 0),
                    agent_key=payload.get("agent_key"),
                    ts=event_ts,
                )

            elif kind == "step_end":  # Canonical: step_complete/step_error -> step_end
                self.record_step_end(
                    run_id=run_id,
                    flow_key=flow_key,
                    step_id=step_id,
                    status=payload.get("status", "succeeded"),
                    duration_ms=payload.get("duration_ms", 0),
                    prompt_tokens=payload.get("prompt_tokens", 0),
                    completion_tokens=payload.get("completion_tokens", 0),
                    handoff_status=payload.get("handoff_status"),
                    routing_decision=payload.get("routing_decision"),
                    routing_next_step=payload.get("routing_next_step"),
                    routing_confidence=payload.get("routing_confidence"),
                    error_message=payload.get("error"),
                    ts=event_ts,
                )

            elif kind == "tool_start":
                # We'll update on tool_end
                pass

            elif kind == "tool_end":
                self.record_tool_call(
                    run_id=run_id,
                    step_id=step_id,
                    tool_name=payload.get("tool", "unknown"),
                    phase=payload.get("phase", "work"),
                    duration_ms=payload.get("duration_ms", 0),
                    success=payload.get("success", True),
                    target_path=payload.get("target_path"),
                    diff_lines_added=payload.get("diff_lines_added"),
                    diff_lines_removed=payload.get("diff_lines_removed"),
                    exit_code=payload.get("exit_code"),
                    error_message=payload.get("error"),
                    ts=event_ts,
                )

            elif kind == "file_changes":
                # File changes from DiffScanner (forensic truth)
                files = payload.get("files", [])
                for fc in files:
                    self.record_file_change(
                        run_id=run_id,
                        step_id=step_id,
                        file_path=fc.get("path", ""),
                        change_type=fc.get("status", "modified"),
                        lines_added=fc.get("insertions", 0),
                        lines_removed=fc.get("deletions", 0),
                        ts=event_ts,
                    )

            elif kind == "route_decision":
                # Routing decisions from the router/navigator
                # Extract explanation if present (may contain nested elimination_log, metrics)
                explanation = payload.get("explanation")

                # Map the method field to routing_mode
                method = payload.get("method", "")
                routing_mode = method if method else None

                # Determine routing_source based on method
                # - "deterministic" -> "fast_path" or "deterministic_fallback"
                # - "llm_tiebreak" -> "navigator"
                # - "no_candidates" -> "deterministic_fallback"
                routing_source = None
                if method == "deterministic":
                    routing_source = "fast_path"
                elif method == "llm_tiebreak":
                    routing_source = "navigator"
                elif method == "no_candidates":
                    routing_source = "deterministic_fallback"

                # Extract candidate count from explanation if available
                candidate_count = 0
                if explanation and isinstance(explanation, dict):
                    candidate_count = explanation.get("candidates_evaluated", 0)

                # Derive decision from method and terminate flag
                terminate = payload.get("terminate", False)
                decision = "terminate" if terminate else "advance"
                if method == "llm_tiebreak":
                    decision = "advance"  # LLM chose a path to advance

                self.record_routing_decision(
                    run_id=run_id,
                    step_seq=event.get("seq", 0),
                    flow_id=flow_key,
                    station_id=step_id,
                    decision=decision,
                    routing_mode=routing_mode,
                    routing_source=routing_source,
                    chosen_candidate_id=payload.get("selected_edge"),
                    candidate_count=candidate_count,
                    target_node=payload.get("target_node"),
                    terminate=terminate,
                    needs_human=payload.get("needs_human", False),
                    explanation=explanation,
                    ts=event_ts,
                )

            elif kind == "run_started":  # Canonical: run_start -> run_started
                # Run initialization
                flow_keys = payload.get("flow_keys", [])
                self.record_run_start(
                    run_id=run_id,
                    flow_keys=flow_keys,
                    profile_id=payload.get("profile_id"),
                    engine_id=payload.get("engine"),
                    metadata=payload.get("metadata"),
                    ts=event_ts,
                )

            elif kind == "run_completed":
                # Run completion
                self.record_run_end(
                    run_id=run_id,
                    status=payload.get("status", "completed"),
                    total_steps=payload.get("total_steps", 0),
                    completed_steps=payload.get("steps_completed", 0),
                    total_tokens=payload.get("total_tokens", 0),
                    total_duration_ms=payload.get("duration_ms", 0),
                    ts=event_ts,
                )

        return newly_ingested
