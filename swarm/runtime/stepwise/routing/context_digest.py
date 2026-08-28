"""
context_digest.py - Build a compact routing context digest for the Navigator.

The Navigator is a cheap, bounded LLM call. It should not receive raw step
output; it receives forensics. This module compresses the signals that informed
a routing decision into a short, deterministic string that is:

- cheap to send (bounded length, no raw transcripts);
- readable in the audit trail (`RUN_BASE/<flow>/routing/`);
- safe to build (never raises on partial or malformed context).

The digest is a diagnostic summary, not an authority. Routing decisions are made
from the structured forensics; the digest exists so a human reading a routing
record can see *why* without re-reading the full context.

Usage:
    from swarm.runtime.stepwise.routing.context_digest import build_context_digest

    digest = build_context_digest(
        flow_key="build",
        step_id="3",
        iteration=2,
        step_result={"status": "UNVERIFIED"},
        verification_result={"passed": False, "failure_summary": "2 tests failed"},
        file_changes={"files_added": 1, "files_modified": 3},
        ...
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Hard ceiling on the rendered digest. The Navigator prompt truncates context to
# 500 chars, so anything longer is wasted tokens.
MAX_DIGEST_CHARS = 500

# Per-field ceiling so one long failure summary cannot crowd out other signals.
MAX_FIELD_CHARS = 120


def _get(source: Any, key: str, default: Any = None) -> Any:
    """Read a key from a mapping or an attribute from an object.

    Routing context arrives as dicts in some paths and dataclasses in others.
    This reads either shape without raising.
    """
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _clip(value: Any, limit: int = MAX_FIELD_CHARS) -> str:
    """Render a value as a single-line string bounded to `limit` characters."""
    text = " ".join(str(value).split())
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _file_change_part(file_changes: Any) -> Optional[str]:
    """Summarize file mutations as `files=+A~M-D`, or None if nothing is known.

    Accepts both count fields (`files_added`) and list fields (`added`), since
    diff scan results are serialized differently across call sites.
    """
    if not file_changes:
        return None

    def count(*keys: str) -> Optional[int]:
        for key in keys:
            raw = _get(file_changes, key)
            if raw is None:
                continue
            if isinstance(raw, (list, tuple, set)):
                return len(raw)
            if isinstance(raw, bool):
                continue
            if isinstance(raw, int):
                return raw
        return None

    added = count("files_added", "added", "added_files")
    modified = count("files_modified", "modified", "modified_files")
    deleted = count("files_deleted", "deleted", "deleted_files")

    if added is None and modified is None and deleted is None:
        total = count("total_files", "files_changed", "file_count")
        if total is None:
            return None
        return f"files={total}"

    return f"files=+{added or 0}~{modified or 0}-{deleted or 0}"


def build_context_digest(
    flow_key: str,
    step_id: str,
    iteration: int,
    step_result: Any = None,
    verification_result: Any = None,
    file_changes: Any = None,
    previous_envelope: Any = None,
    forensic_verdict: Optional[Dict[str, Any]] = None,
    loop_state: Optional[Dict[str, int]] = None,
    candidate_count: Optional[int] = None,
) -> str:
    """Build a compact digest of the context informing a routing decision.

    Every field is optional. Absent signals are omitted rather than rendered as
    empty or false values, so the digest never implies a measurement that was
    not taken.

    Args:
        flow_key: The flow being executed.
        step_id: The step that just ran.
        iteration: Current iteration count for this step.
        step_result: Step execution result (dict or object with `status`).
        verification_result: Verification results (`passed`, `failure_summary`).
        file_changes: Forensic diff scan results.
        previous_envelope: Prior step's handoff envelope.
        forensic_verdict: Claim-vs-evidence verdict, if computed.
        loop_state: Microloop iteration counters.
        candidate_count: Number of routing candidates offered.

    Returns:
        A bounded `key=value; ...` string. Never raises; on unexpected input it
        degrades to the position fields it could read.
    """
    parts: List[str] = [f"flow={flow_key}", f"step={step_id}", f"iter={iteration}"]

    try:
        status = _get(step_result, "status")
        if status:
            parts.append(f"status={_clip(status, 32)}")

        if verification_result is not None:
            passed = _get(verification_result, "passed")
            if passed is not None:
                parts.append(f"verify={'pass' if passed else 'fail'}")
                if not passed:
                    failure = _get(verification_result, "failure_summary") or _get(
                        verification_result, "summary"
                    )
                    if failure:
                        parts.append(f"failure={_clip(failure)}")

        file_part = _file_change_part(file_changes)
        if file_part:
            parts.append(file_part)

        if previous_envelope is not None:
            prev_step = _get(previous_envelope, "step_id")
            prev_status = _get(previous_envelope, "status")
            if prev_step:
                label = f"prev={_clip(prev_step, 40)}"
                if prev_status:
                    label += f":{_clip(prev_status, 24)}"
                parts.append(label)

        if forensic_verdict:
            recommendation = forensic_verdict.get("recommendation")
            if recommendation:
                confidence = forensic_verdict.get("confidence")
                if isinstance(confidence, (int, float)):
                    parts.append(f"forensic={recommendation}({confidence:.2f})")
                else:
                    parts.append(f"forensic={_clip(recommendation, 32)}")
            flags = forensic_verdict.get("reward_hacking_flags") or []
            if flags:
                parts.append(f"flags={_clip(','.join(str(f) for f in flags), 80)}")

        if loop_state:
            active = {k: v for k, v in loop_state.items() if v}
            if active:
                rendered = ",".join(f"{k}:{v}" for k, v in sorted(active.items()))
                parts.append(f"loops={_clip(rendered, 80)}")

        if candidate_count is not None:
            parts.append(f"candidates={candidate_count}")
    except Exception as exc:  # pragma: no cover - defensive; digest is diagnostic
        logger.debug("Context digest degraded for step %s: %s", step_id, exc)

    digest = "; ".join(parts)
    if len(digest) > MAX_DIGEST_CHARS:
        return digest[: MAX_DIGEST_CHARS - 1] + "…"
    return digest
