"""
navigator.py - Navigator-based routing for stepwise execution.

This module provides the Navigator routing strategy for intelligent routing
decisions. It implements the candidate-set pattern where:

1. Python generates routing candidates from the graph and context
2. Navigator (LLM) intelligently chooses among candidates
3. Python validates the choice and produces a RoutingOutcome

This module extracts the Navigator routing logic from the StepwiseOrchestrator
to enable use by the unified routing driver.

Usage:
    from swarm.runtime.stepwise.routing.navigator import route_via_navigator

    outcome = route_via_navigator(
        step=current_step,
        step_result=result,
        run_state=state,
        navigation_orchestrator=nav_orch,
        ...
    )
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from swarm.runtime.forensic_comparator import (
    compare_claim_vs_evidence,
    forensic_verdict_to_dict,
)
from swarm.runtime.forensic_types import diff_scan_result_from_dict
from swarm.runtime.handoff_io import update_envelope_routing
from swarm.runtime.stepwise._routing_legacy import generate_routing_candidates
from swarm.runtime.types import (
    RoutingDecision,
    RoutingMode,
    handoff_envelope_to_dict,
)

from .driver import RoutingOutcome

# Import from utility_candidates.py to avoid circular imports with driver.py
# The utility_candidates module is the single source of truth for candidate generation
from .utility_candidates import get_utility_flow_candidates as _get_utility_flow_candidates

if TYPE_CHECKING:
    from swarm.config.flow_registry import FlowDefinition, StepDefinition
    from swarm.runtime.navigator_integration import NavigationOrchestrator
    from swarm.runtime.router import FlowGraph
    from swarm.runtime.types import RunSpec, RunState

logger = logging.getLogger(__name__)


def build_context_digest(
    step_id: str,
    iteration: int,
    step_result: Dict[str, Any],
    verification_result: Optional[Dict[str, Any]] = None,
    file_changes: Optional[Dict[str, Any]] = None,
    forensic_verdict: Optional[Dict[str, Any]] = None,
    loop_state: Optional[Dict[str, int]] = None,
) -> str:
    """Build a compact digest of the context that informed a routing decision.

    The digest is a single line of ``key=value`` clauses covering the signals
    the Navigator actually routes on: where we are, whether verification
    passed, what changed on disk, and whether the forensic comparator trusts
    the step's claims. It is fed to the Navigator as ``context`` and persisted
    alongside the candidate set so a routing decision can be audited without
    re-reading the full step output.

    Every field is optional. Signals that were not measured are omitted rather
    than defaulted, so an absent clause means "not measured", not "zero".

    Args:
        step_id: The step being routed away from.
        iteration: Current iteration count for this step.
        step_result: Step execution result (status, duration_ms).
        verification_result: Verification check results, if any were run.
        file_changes: Diff scan output, if a scan ran.
        forensic_verdict: Claim-vs-evidence verdict, if one was computed.
        loop_state: Microloop iteration state, if this step loops.

    Returns:
        A compact single-line digest. Never raises; on unexpected input shapes
        the affected clause is dropped.
    """
    parts: List[str] = [f"step={step_id}", f"iter={iteration}"]

    status = step_result.get("status")
    if status:
        parts.append(f"status={status}")

    duration_ms = step_result.get("duration_ms")
    if duration_ms:
        parts.append(f"duration_ms={duration_ms}")

    if verification_result:
        checks = verification_result.get("checks", []) or []
        failed = [c for c in checks if not c.get("passed", True)]
        parts.append(f"verify={'pass' if verification_result.get('passed', True) else 'fail'}")
        if checks:
            parts.append(f"checks={len(checks) - len(failed)}/{len(checks)}")
        if failed:
            names = [str(c.get("name") or c.get("message") or "unknown") for c in failed[:3]]
            suffix = f" (+{len(failed) - 3})" if len(failed) > 3 else ""
            parts.append(f"failed=[{', '.join(names)}{suffix}]")

    if file_changes:
        files = file_changes.get("files", []) or []
        insertions = file_changes.get("total_insertions", 0)
        deletions = file_changes.get("total_deletions", 0)
        parts.append(f"files={len(files)}")
        parts.append(f"lines=+{insertions}/-{deletions}")
        untracked = file_changes.get("untracked", []) or []
        if untracked:
            parts.append(f"untracked={len(untracked)}")
        if file_changes.get("scan_error"):
            parts.append("scan=error")

    if forensic_verdict:
        parts.append(f"claim={'ok' if forensic_verdict.get('claim_verified', True) else 'suspect'}")
        confidence = forensic_verdict.get("confidence")
        if confidence is not None:
            parts.append(f"confidence={float(confidence):.2f}")
        recommendation = forensic_verdict.get("recommendation")
        if recommendation:
            parts.append(f"verdict={recommendation}")
        flags = forensic_verdict.get("reward_hacking_flags", []) or []
        if flags:
            parts.append(f"flags=[{', '.join(str(f) for f in flags[:3])}]")

    if loop_state:
        loops = loop_state.get(step_id)
        if loops:
            parts.append(f"loops={loops}")

    return " ".join(parts)


def route_via_navigator(
    step: "StepDefinition",
    step_result: Any,
    run_state: "RunState",
    loop_state: Dict[str, int],
    iteration: int,
    routing_mode: RoutingMode,
    navigation_orchestrator: "NavigationOrchestrator",
    run_id: str,
    flow_key: str,
    flow_graph: "FlowGraph",
    flow_def: "FlowDefinition",
    spec: "RunSpec",
    run_base: Path,
    # Utility flow detection
    git_status: Optional[Dict[str, Any]] = None,
    repo_root: Optional[Path] = None,
) -> RoutingOutcome:
    """Route using NavigationOrchestrator with candidate-set pattern.

    Generates routing candidates from the graph, passes them to Navigator,
    and validates the chosen candidate. This implements the candidate-set
    pattern where Python generates options and Navigator intelligently chooses.

    Args:
        step: The current step definition.
        step_result: Result from step execution.
        run_state: Current run state.
        loop_state: Microloop iteration state.
        iteration: Current iteration count for this step.
        routing_mode: Current routing mode (ASSIST or AUTHORITATIVE).
        navigation_orchestrator: The Navigator orchestrator instance.
        run_id: The run identifier.
        flow_key: The flow key.
        flow_graph: The FlowGraph for edge candidates.
        flow_def: The flow definition for candidate generation.
        spec: The run specification.
        run_base: Path to the run base directory.
        git_status: Git status for utility flow detection (behind_count, diverged).
        repo_root: Repository root path for utility flow registry.

    Returns:
        RoutingOutcome with the Navigator's decision and full audit trail.
    """
    # Build step result dict for Navigator
    step_result_dict = {
        "status": step_result.status
        if hasattr(step_result, "status")
        else step_result.get("status", ""),
        "output": step_result.output
        if hasattr(step_result, "output")
        else step_result.get("output", ""),
        "duration_ms": step_result.duration_ms
        if hasattr(step_result, "duration_ms")
        else step_result.get("duration_ms", 0),
    }

    # Get file changes from step result if available
    file_changes = None
    if hasattr(step_result, "file_changes"):
        file_changes = step_result.file_changes

    # Get verification result if available
    verification_result = None
    if hasattr(step_result, "verification_result"):
        verification_result = step_result.verification_result

    # Try to read previous envelope for context
    previous_envelope = None
    if step.id in run_state.handoff_envelopes:
        previous_envelope = run_state.handoff_envelopes[step.id]

    # =================================================================
    # FORENSIC VERDICT COMPUTATION: Compare claims vs evidence
    # =================================================================
    forensic_verdict: Optional[Dict[str, Any]] = None
    if previous_envelope is not None:
        try:
            handoff_dict = handoff_envelope_to_dict(previous_envelope)
            diff_result = None
            if file_changes:
                try:
                    diff_result = diff_scan_result_from_dict(file_changes)
                except Exception as e:
                    logger.debug(
                        "Could not convert file_changes to DiffScanResult: %s",
                        e,
                    )

            verdict = compare_claim_vs_evidence(
                handoff=handoff_dict,
                diff_result=diff_result,
                test_summary=None,
            )

            forensic_verdict = forensic_verdict_to_dict(verdict)

            logger.debug(
                "Forensic verdict for step %s: recommendation=%s, confidence=%.2f, flags=%s",
                step.id,
                verdict.recommendation.value,
                verdict.confidence,
                [f.value for f in verdict.reward_hacking_flags],
            )
        except Exception as e:
            logger.warning(
                "Failed to compute forensic verdict for step %s: %s",
                step.id,
                e,
            )

    # =================================================================
    # CANDIDATE-SET PATTERN: Generate routing candidates from graph
    # =================================================================
    sidequest_options = None
    if navigation_orchestrator is not None:
        catalog = navigation_orchestrator.sidequest_catalog
        trigger_context = {
            "verification_passed": verification_result.get("passed", True)
            if verification_result
            else True,
            "iteration": iteration,
        }
        applicable = catalog.get_applicable_sidequests(trigger_context, run_id)
        sidequest_options = [
            {
                "sidequest_id": sq.sidequest_id,
                "name": sq.description,
                "priority": sq.priority,
            }
            for sq in applicable
        ]

    # Generate routing candidates with forensic priority shaping
    candidates = generate_routing_candidates(
        step=step,
        step_result=step_result_dict,
        flow_def=flow_def,
        loop_state=loop_state,
        run_state=run_state,
        sidequest_options=sidequest_options,
        forensic_verdict=forensic_verdict,
    )

    # =================================================================
    # UTILITY FLOW CANDIDATES: Add inject_flow:* candidates BEFORE Navigator
    # =================================================================
    # This is the critical integration point: utility flow candidates must be
    # part of the candidate set the Navigator sees, not added after the decision.
    # The candidate-set pattern requires: Python generates → Navigator chooses.
    utility_candidates = _get_utility_flow_candidates(
        step_result=step_result,
        run_state=run_state,
        git_status=git_status,
        repo_root=repo_root,
    )

    if utility_candidates:
        # Add utility flow candidates to the list before Navigator sees them
        existing_ids = {c.candidate_id for c in candidates}
        for uf_candidate in utility_candidates:
            if uf_candidate.candidate_id not in existing_ids:
                candidates.append(uf_candidate)

        logger.info(
            "Added %d utility flow candidates for step %s: %s",
            len(utility_candidates),
            step.id,
            [c.candidate_id for c in utility_candidates],
        )

    # Convert RoutingCandidate objects to dicts for Navigator
    routing_candidates = [
        {
            "candidate_id": c.candidate_id,
            "action": c.action,
            "target_node": c.target_node,
            "reason": c.reason,
            "priority": c.priority,
            "source": c.source,
            "is_default": c.is_default,
        }
        for c in candidates
    ]

    logger.debug(
        "Generated %d routing candidates for step %s: %s",
        len(routing_candidates),
        step.id,
        [c["candidate_id"] for c in routing_candidates],
    )

    # Build a compact digest of the signals that informed this decision.
    # Passed to the Navigator as `context` and persisted for audit below.
    context_digest = build_context_digest(
        step_id=step.id,
        iteration=iteration,
        step_result=step_result_dict,
        verification_result=verification_result,
        file_changes=file_changes,
        forensic_verdict=forensic_verdict,
        loop_state=loop_state,
    )

    logger.debug("Context digest for step %s: %s", step.id, context_digest)

    # Call NavigationOrchestrator.navigate() with candidates
    nav_result = navigation_orchestrator.navigate(
        run_id=run_id,
        flow_key=flow_key,
        current_node=step.id,
        iteration=iteration,
        flow_graph=flow_graph,
        step_result=step_result_dict,
        verification_result=verification_result,
        file_changes=file_changes,
        run_state=run_state,
        context_digest=context_digest,
        previous_envelope=previous_envelope,
        no_human_mid_flow=spec.no_human_mid_flow,
        routing_candidates=routing_candidates,
    )

    # Extract routing decision from NavigationResult
    next_step_id = nav_result.next_node
    routing_signal = nav_result.routing_signal

    reason = routing_signal.reason or "navigator_decision"
    routing_source = "navigator"

    # If detour was injected, note it in the reason
    if nav_result.detour_injected:
        routing_source = "navigator:detour"
        reason = f"Detour: {reason}"
    elif nav_result.extend_graph_injected:
        routing_source = "navigator:extend_graph"
        reason = f"Extend graph: {reason}"

    # =================================================================
    # PERSIST ROUTING DECISION TO ENVELOPE
    # =================================================================
    candidate_set_path: Optional[str] = None
    if routing_candidates:
        try:
            routing_dir = run_base / "routing"
            routing_dir.mkdir(parents=True, exist_ok=True)

            candidate_file = routing_dir / f"candidates_step_{step.id}.json"
            candidate_set_path = f"routing/candidates_step_{step.id}.json"

            with open(candidate_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "step_id": step.id,
                        "context_digest": context_digest,
                        "candidate_count": len(routing_candidates),
                        "candidates": routing_candidates,
                    },
                    f,
                    indent=2,
                )
            logger.debug(
                "Wrote %d routing candidates to %s",
                len(routing_candidates),
                candidate_file,
            )
        except Exception as e:
            logger.warning("Failed to write routing candidates to artifact file: %s", e)
            candidate_set_path = None

    routing_dict = {
        "decision": routing_signal.decision.value
        if hasattr(routing_signal.decision, "value")
        else str(routing_signal.decision),
        "next_step_id": next_step_id,
        "reason": reason,
        "confidence": routing_signal.confidence,
        "needs_human": routing_signal.needs_human,
        "chosen_candidate_id": routing_signal.chosen_candidate_id,
        "candidate_count": len(routing_candidates),
        "candidate_ids": [c.get("candidate_id") for c in routing_candidates],
        "candidate_set_path": candidate_set_path,
        "routing_source": routing_source,
        "context_digest": context_digest,
    }
    updated = update_envelope_routing(
        run_base=run_base,
        step_id=step.id,
        routing_signal=routing_dict,
    )
    if updated:
        logger.debug(
            "Navigator: Persisted routing to envelope for step %s: "
            "next=%s, chosen_candidate=%s, candidates=%d",
            step.id,
            next_step_id,
            routing_signal.chosen_candidate_id,
            len(routing_candidates),
        )

    # =================================================================
    # BUILD ROUTING OUTCOME
    # =================================================================
    # Map Navigator's decision to a RoutingDecision
    decision = routing_signal.decision
    if hasattr(decision, "value"):
        decision_str = decision.value
    else:
        decision_str = str(decision)

    # Map decision string to RoutingDecision enum
    decision_map = {
        "CONTINUE": RoutingDecision.ADVANCE,
        "ADVANCE": RoutingDecision.ADVANCE,
        "LOOP": RoutingDecision.LOOP,
        "REPEAT": RoutingDecision.LOOP,
        "TERMINATE": RoutingDecision.TERMINATE,
        "ESCALATE": RoutingDecision.SKIP,  # Map escalate to skip for now
        "DETOUR": RoutingDecision.BRANCH,
        "BRANCH": RoutingDecision.BRANCH,
        "SKIP": RoutingDecision.SKIP,
    }
    mapped_decision = decision_map.get(decision_str.upper(), RoutingDecision.ADVANCE)

    return RoutingOutcome(
        decision=mapped_decision,
        next_step_id=next_step_id,
        reason=reason,
        confidence=routing_signal.confidence,
        needs_human=routing_signal.needs_human,
        routing_source=routing_source,
        chosen_candidate_id=routing_signal.chosen_candidate_id,
        candidates=candidates,
        loop_iteration=iteration,
        exit_condition_met=(mapped_decision == RoutingDecision.TERMINATE),
        signal=routing_signal,
    )
