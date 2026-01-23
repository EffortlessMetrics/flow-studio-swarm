from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .models import Fact, RoutingDecisionRecord, RunStats, StepStats, ToolBreakdown

logger = logging.getLogger(__name__)


class StatsDBQueryMixin:
    def get_run_stats(self, run_id: str) -> Optional[RunStats]:
        """Get aggregated statistics for a run."""
        if self.connection is None:
            return None

        with self._lock:
            result = self.connection.execute(
                """
                SELECT
                    r.run_id,
                    r.flow_keys,
                    r.status,
                    r.started_at,
                    r.completed_at,
                    r.total_steps,
                    r.completed_steps,
                    r.total_tokens,
                    r.total_duration_ms,
                    (SELECT COUNT(*) FROM tool_calls WHERE run_id = r.run_id) as tool_call_count,
                    (SELECT COUNT(*) FROM file_changes WHERE run_id = r.run_id) as file_change_count
                FROM runs r
                WHERE r.run_id = ?
                """,
                [run_id],
            ).fetchone()

            if result is None:
                return None

            return RunStats(
                run_id=result[0],
                flow_keys=result[1] or [],
                status=result[2],
                started_at=result[3],
                completed_at=result[4],
                total_steps=result[5] or 0,
                completed_steps=result[6] or 0,
                total_tokens=result[7] or 0,
                total_duration_ms=result[8] or 0,
                tool_call_count=result[9] or 0,
                file_change_count=result[10] or 0,
            )

    def get_step_stats(self, run_id: str) -> List[StepStats]:
        """Get statistics for all steps in a run."""
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    s.step_id,
                    s.flow_key,
                    s.agent_key,
                    s.status,
                    s.duration_ms,
                    s.total_tokens,
                    s.handoff_status,
                    s.routing_decision,
                    (SELECT COUNT(*) FROM tool_calls WHERE run_id = s.run_id AND step_id = s.step_id) as tool_calls
                FROM steps s
                WHERE s.run_id = ?
                ORDER BY s.step_index
                """,
                [run_id],
            ).fetchall()

            return [
                StepStats(
                    step_id=row[0],
                    flow_key=row[1],
                    agent_key=row[2],
                    status=row[3],
                    duration_ms=row[4] or 0,
                    total_tokens=row[5] or 0,
                    handoff_status=row[6],
                    routing_decision=row[7],
                    tool_calls=row[8] or 0,
                )
                for row in results
            ]

    def get_tool_breakdown(self, run_id: str) -> List[ToolBreakdown]:
        """Get breakdown of tool usage for a run."""
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    tool_name,
                    COUNT(*) as call_count,
                    SUM(duration_ms) as total_duration_ms,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(duration_ms) as avg_duration_ms
                FROM tool_calls
                WHERE run_id = ?
                GROUP BY tool_name
                ORDER BY call_count DESC
                """,
                [run_id],
            ).fetchall()

            return [
                ToolBreakdown(
                    tool_name=row[0],
                    call_count=row[1],
                    total_duration_ms=row[2] or 0,
                    success_rate=row[3] or 1.0,
                    avg_duration_ms=row[4] or 0.0,
                )
                for row in results
            ]

    def get_recent_runs(self, limit: int = 20) -> List[RunStats]:
        """Get recent runs for the UI dashboard."""
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    r.run_id,
                    r.flow_keys,
                    r.status,
                    r.started_at,
                    r.completed_at,
                    r.total_steps,
                    r.completed_steps,
                    r.total_tokens,
                    r.total_duration_ms,
                    (SELECT COUNT(*) FROM tool_calls WHERE run_id = r.run_id) as tool_call_count,
                    (SELECT COUNT(*) FROM file_changes WHERE run_id = r.run_id) as file_change_count
                FROM runs r
                ORDER BY r.started_at DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()

            return [
                RunStats(
                    run_id=row[0],
                    flow_keys=row[1] or [],
                    status=row[2],
                    started_at=row[3],
                    completed_at=row[4],
                    total_steps=row[5] or 0,
                    completed_steps=row[6] or 0,
                    total_tokens=row[7] or 0,
                    total_duration_ms=row[8] or 0,
                    tool_call_count=row[9] or 0,
                    file_change_count=row[10] or 0,
                )
                for row in results
            ]

    def get_file_changes(self, run_id: str) -> List[Dict[str, Any]]:
        """Get file changes for a run."""
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT file_path, change_type, lines_added, lines_removed, step_id, timestamp
                FROM file_changes
                WHERE run_id = ?
                ORDER BY timestamp
                """,
                [run_id],
            ).fetchall()

            return [
                {
                    "file_path": row[0],
                    "change_type": row[1],
                    "lines_added": row[2],
                    "lines_removed": row[3],
                    "step_id": row[4],
                    "timestamp": row[5].isoformat() if row[5] else None,
                }
                for row in results
            ]

    def get_facts_for_run(self, run_id: str) -> List[Fact]:
        """Get all facts extracted for a run.

        Args:
            run_id: The run ID to query.

        Returns:
            List of Fact objects for the run, ordered by step_id and marker_id.
        """
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    fact_id, run_id, step_id, flow_key, agent_key,
                    marker_type, marker_id, fact_type, content,
                    priority, status, evidence, created_at, extracted_at, metadata
                FROM facts
                WHERE run_id = ?
                ORDER BY step_id, marker_id
                """,
                [run_id],
            ).fetchall()

            return [
                Fact(
                    fact_id=row[0],
                    run_id=row[1],
                    step_id=row[2],
                    flow_key=row[3],
                    agent_key=row[4],
                    marker_type=row[5],
                    marker_id=row[6],
                    fact_type=row[7],
                    content=row[8],
                    priority=row[9],
                    status=row[10],
                    evidence=row[11],
                    created_at=row[12],
                    extracted_at=row[13],
                    metadata=json.loads(row[14]) if row[14] else {},
                )
                for row in results
            ]

    def get_facts_by_marker_type(self, run_id: str, marker_type: str) -> List[Fact]:
        """Get facts for a run filtered by marker type.

        Args:
            run_id: The run ID to query.
            marker_type: The marker type to filter by (REQ, SOL, TRC, ASM, DEC, etc.).

        Returns:
            List of Fact objects matching the marker type, ordered by marker_id.
        """
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    fact_id, run_id, step_id, flow_key, agent_key,
                    marker_type, marker_id, fact_type, content,
                    priority, status, evidence, created_at, extracted_at, metadata
                FROM facts
                WHERE run_id = ? AND marker_type = ?
                ORDER BY marker_id
                """,
                [run_id, marker_type],
            ).fetchall()

            return [
                Fact(
                    fact_id=row[0],
                    run_id=row[1],
                    step_id=row[2],
                    flow_key=row[3],
                    agent_key=row[4],
                    marker_type=row[5],
                    marker_id=row[6],
                    fact_type=row[7],
                    content=row[8],
                    priority=row[9],
                    status=row[10],
                    evidence=row[11],
                    created_at=row[12],
                    extracted_at=row[13],
                    metadata=json.loads(row[14]) if row[14] else {},
                )
                for row in results
            ]

    def get_routing_decisions(self, run_id: str) -> List[RoutingDecisionRecord]:
        """Get all routing decisions for a run.

        Args:
            run_id: The run ID to query.

        Returns:
            List of RoutingDecisionRecord objects for the run, ordered by step_seq.
        """
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    run_id, step_seq, flow_id, station_id, routing_mode, routing_source,
                    chosen_candidate_id, candidate_count, decision, target_node,
                    timestamp, terminate, needs_human, explanation
                FROM routing_decisions
                WHERE run_id = ?
                ORDER BY step_seq, timestamp
                """,
                [run_id],
            ).fetchall()

            return [
                RoutingDecisionRecord(
                    run_id=row[0],
                    step_seq=row[1],
                    flow_id=row[2],
                    station_id=row[3],
                    routing_mode=row[4],
                    routing_source=row[5],
                    chosen_candidate_id=row[6],
                    candidate_count=row[7] or 0,
                    decision=row[8],
                    target_node=row[9],
                    timestamp=row[10],
                    terminate=row[11] or False,
                    needs_human=row[12] or False,
                    explanation=json.loads(row[13]) if row[13] else None,
                )
                for row in results
            ]

    def get_routing_decisions_by_flow(
        self, run_id: str, flow_id: str
    ) -> List[RoutingDecisionRecord]:
        """Get routing decisions for a specific flow within a run.

        Args:
            run_id: The run ID to query.
            flow_id: The flow ID to filter by (signal, plan, build, etc.).

        Returns:
            List of RoutingDecisionRecord objects for the flow, ordered by step_seq.
        """
        if self.connection is None:
            return []

        with self._lock:
            results = self.connection.execute(
                """
                SELECT
                    run_id, step_seq, flow_id, station_id, routing_mode, routing_source,
                    chosen_candidate_id, candidate_count, decision, target_node,
                    timestamp, terminate, needs_human, explanation
                FROM routing_decisions
                WHERE run_id = ? AND flow_id = ?
                ORDER BY step_seq, timestamp
                """,
                [run_id, flow_id],
            ).fetchall()

            return [
                RoutingDecisionRecord(
                    run_id=row[0],
                    step_seq=row[1],
                    flow_id=row[2],
                    station_id=row[3],
                    routing_mode=row[4],
                    routing_source=row[5],
                    chosen_candidate_id=row[6],
                    candidate_count=row[7] or 0,
                    decision=row[8],
                    target_node=row[9],
                    timestamp=row[10],
                    terminate=row[11] or False,
                    needs_human=row[12] or False,
                    explanation=json.loads(row[13]) if row[13] else None,
                )
                for row in results
            ]

    def get_routing_decision_summary(self, run_id: str) -> Dict[str, Any]:
        """Get a summary of routing decisions for a run.

        Useful for UI dashboards to show routing statistics at a glance.

        Args:
            run_id: The run ID to query.

        Returns:
            Dict with summary statistics:
            - total_decisions: Total number of routing decisions
            - by_decision: Count by decision type (advance, loop, terminate, etc.)
            - by_routing_mode: Count by routing mode (deterministic, llm_tiebreak, etc.)
            - by_routing_source: Count by routing source (navigator, fast_path, etc.)
            - needs_human_count: Number of decisions flagged for human review
            - terminations: Number of terminate decisions
        """
        if self.connection is None:
            return {
                "total_decisions": 0,
                "by_decision": {},
                "by_routing_mode": {},
                "by_routing_source": {},
                "needs_human_count": 0,
                "terminations": 0,
            }

        with self._lock:
            # Get total and by-decision counts
            total_result = self.connection.execute(
                "SELECT COUNT(*) FROM routing_decisions WHERE run_id = ?",
                [run_id],
            ).fetchone()
            total_decisions = total_result[0] if total_result else 0

            decision_counts = self.connection.execute(
                """
                SELECT decision, COUNT(*) as count
                FROM routing_decisions
                WHERE run_id = ?
                GROUP BY decision
                """,
                [run_id],
            ).fetchall()
            by_decision = {row[0]: row[1] for row in decision_counts}

            mode_counts = self.connection.execute(
                """
                SELECT routing_mode, COUNT(*) as count
                FROM routing_decisions
                WHERE run_id = ? AND routing_mode IS NOT NULL
                GROUP BY routing_mode
                """,
                [run_id],
            ).fetchall()
            by_routing_mode = {row[0]: row[1] for row in mode_counts}

            source_counts = self.connection.execute(
                """
                SELECT routing_source, COUNT(*) as count
                FROM routing_decisions
                WHERE run_id = ? AND routing_source IS NOT NULL
                GROUP BY routing_source
                """,
                [run_id],
            ).fetchall()
            by_routing_source = {row[0]: row[1] for row in source_counts}

            needs_human_result = self.connection.execute(
                "SELECT COUNT(*) FROM routing_decisions WHERE run_id = ? AND needs_human = TRUE",
                [run_id],
            ).fetchone()
            needs_human_count = needs_human_result[0] if needs_human_result else 0

            terminate_result = self.connection.execute(
                "SELECT COUNT(*) FROM routing_decisions WHERE run_id = ? AND terminate = TRUE",
                [run_id],
            ).fetchone()
            terminations = terminate_result[0] if terminate_result else 0

            return {
                "total_decisions": total_decisions,
                "by_decision": by_decision,
                "by_routing_mode": by_routing_mode,
                "by_routing_source": by_routing_source,
                "needs_human_count": needs_human_count,
                "terminations": terminations,
            }
