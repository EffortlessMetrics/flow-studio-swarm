"""
Evolution processor - pure computation logic for evolution patches.

Extracted from autopilot.py to separate orchestration from processing.
This module handles the computation and application of evolution patches,
independent of the autopilot lifecycle.

The processor is designed to be:
1. Testable in isolation (no runtime wiring needed)
2. Policy-gated (respects SUGGEST_ONLY, AUTO_APPLY_SAFE, AUTO_APPLY_ALL)
3. Auditable (all decisions are logged and tracked)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================


class EvolutionApplyPolicy(str, Enum):
    """Policy controlling when evolution patches are applied.

    Attributes:
        SUGGEST_ONLY: Generate suggestions but never auto-apply. Default.
        AUTO_APPLY_SAFE: Auto-apply patches marked as safe (low risk, high confidence).
        AUTO_APPLY_ALL: Auto-apply all patches regardless of risk level.
    """

    SUGGEST_ONLY = "suggest_only"
    AUTO_APPLY_SAFE = "auto_apply_safe"
    AUTO_APPLY_ALL = "auto_apply_all"


class EvolutionBoundary(str, Enum):
    """When evolution patches can be processed.

    Attributes:
        RUN_END: Only at the end of a complete autopilot run.
        FLOW_END: At the end of each flow (wisdom flow specifically).
        NEVER: Never process evolution patches.
    """

    RUN_END = "run_end"
    FLOW_END = "flow_end"
    NEVER = "never"


@dataclass
class EvolutionSuggestion:
    """A recorded evolution suggestion, whether applied or not.

    Attributes:
        patch_id: Unique identifier for the patch.
        target_file: File that would be modified.
        patch_type: Type of patch (flow_spec, station_spec, etc.).
        reasoning: Why this patch was suggested.
        confidence: Confidence level (high, medium, low).
        risk: Risk level (low, medium, high).
        action_taken: What happened (suggested, applied, rejected).
        rejection_reason: If rejected, why.
        applied_at: Timestamp if applied.
        source_run_id: Run that generated this suggestion.
    """

    patch_id: str
    target_file: str
    patch_type: str
    reasoning: str
    confidence: str
    risk: str
    action_taken: str  # "suggested", "applied", "rejected"
    rejection_reason: Optional[str] = None
    applied_at: Optional[str] = None
    source_run_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "patch_id": self.patch_id,
            "target_file": self.target_file,
            "patch_type": self.patch_type,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "risk": self.risk,
            "action_taken": self.action_taken,
            "rejection_reason": self.rejection_reason,
            "applied_at": self.applied_at,
            "source_run_id": self.source_run_id,
        }


@dataclass
class EvolutionResult:
    """Result of processing evolution patches.

    Attributes:
        patches_processed: Total patches considered.
        patches_applied: Number of patches successfully applied.
        patches_rejected: Number of patches rejected due to validation.
        patches_skipped: Number of patches skipped (already applied/rejected).
        patches_suggested: Number of patches recorded as suggestions only.
        applied_patch_ids: IDs of successfully applied patches.
        rejected_patch_ids: IDs of rejected patches with reasons.
        suggestions: All evolution suggestions recorded (applied or not).
    """

    patches_processed: int = 0
    patches_applied: int = 0
    patches_rejected: int = 0
    patches_skipped: int = 0
    patches_suggested: int = 0
    applied_patch_ids: List[str] = field(default_factory=list)
    rejected_patch_ids: List[Dict[str, str]] = field(default_factory=list)
    suggestions: List[EvolutionSuggestion] = field(default_factory=list)


@dataclass
class EvolutionConfig:
    """Configuration for evolution processing.

    Attributes:
        policy: Policy controlling evolution patch application.
        boundary: When evolution patches can be processed.
        patch_types: List of patch types to process.
        repo_root: Repository root path for applying patches.
        emit_events: Whether to emit events (requires storage module).
    """

    policy: EvolutionApplyPolicy = EvolutionApplyPolicy.SUGGEST_ONLY
    boundary: EvolutionBoundary = EvolutionBoundary.RUN_END
    patch_types: List[str] = field(default_factory=lambda: ["flow_evolution", "station_tuning"])
    repo_root: Optional[Path] = None
    emit_events: bool = True


# =============================================================================
# Event Emitter Protocol
# =============================================================================


class EventEmitter:
    """Protocol for emitting evolution events.

    This allows the processor to be tested without the storage module.
    """

    def emit(
        self,
        run_id: str,
        event_kind: str,
        flow_key: str,
        payload: Dict[str, Any],
    ) -> None:
        """Emit an event. Default implementation does nothing."""
        pass


class StorageEventEmitter(EventEmitter):
    """Event emitter that uses the storage module."""

    def emit(
        self,
        run_id: str,
        event_kind: str,
        flow_key: str,
        payload: Dict[str, Any],
    ) -> None:
        """Emit an event using the storage module."""
        from swarm.runtime import storage as storage_module
        from swarm.runtime.types import RunEvent

        storage_module.append_event(
            run_id,
            RunEvent(
                run_id=run_id,
                ts=datetime.now(timezone.utc),
                kind=event_kind,
                flow_key=flow_key,
                payload=payload,
            ),
        )


# =============================================================================
# Evolution Processor
# =============================================================================


class EvolutionProcessor:
    """Pure processor for evolution patches.

    This class handles the computation and application of evolution patches,
    independent of the autopilot lifecycle. It can be used:
    - At run end (by AutopilotController)
    - At flow end (by the orchestrator)
    - Manually (for testing or debugging)

    Example:
        processor = EvolutionProcessor(
            config=EvolutionConfig(
                policy=EvolutionApplyPolicy.AUTO_APPLY_SAFE,
                repo_root=Path("/path/to/repo"),
            ),
        )
        result = processor.process(
            wisdom_dir=Path("/path/to/run/wisdom"),
            run_id="run-123",
            boundary="run_end",
        )
    """

    def __init__(
        self,
        config: EvolutionConfig,
        event_emitter: Optional[EventEmitter] = None,
    ):
        """Initialize the evolution processor.

        Args:
            config: Configuration for evolution processing.
            event_emitter: Optional event emitter. Defaults to StorageEventEmitter
                if emit_events is True, otherwise NoOpEmitter.
        """
        self.config = config
        self._event_emitter = event_emitter
        if self._event_emitter is None:
            if config.emit_events:
                self._event_emitter = StorageEventEmitter()
            else:
                self._event_emitter = EventEmitter()

    def process(
        self,
        wisdom_dir: Path,
        run_id: str,
        boundary: str = "run_end",
    ) -> EvolutionResult:
        """Process evolution patches from wisdom artifacts.

        Policy-gated evolution processing. Based on the policy:
        - SUGGEST_ONLY: Record suggestions, emit evolution_suggested events, never apply
        - AUTO_APPLY_SAFE: Apply only safe patches (low risk, high confidence)
        - AUTO_APPLY_ALL: Apply all valid patches

        Args:
            wisdom_dir: Path to the wisdom directory containing evolution artifacts.
            run_id: The run identifier for event emission.
            boundary: The boundary type ("flow_end" or "run_end").

        Returns:
            EvolutionResult with summary of processed patches.
        """
        from swarm.runtime.evolution import (
            PatchType,
            apply_evolution_patch,
            generate_evolution_patch,
            validate_evolution_patch,
        )

        result = EvolutionResult()
        policy = self.config.policy
        repo_root = self.config.repo_root

        if not wisdom_dir.exists():
            logger.warning(
                "Wisdom directory not found for evolution processing: %s",
                wisdom_dir,
            )
            return result

        # Emit evolution processing started event
        self._emit(
            run_id=run_id,
            event_kind="evolution_processing_started",
            flow_key="wisdom",
            payload={
                "policy": policy.value,
                "boundary": boundary,
                "patch_types": self.config.patch_types,
            },
        )

        # Map patch type strings to PatchType enum
        type_mapping = {
            "flow_evolution": [PatchType.FLOW_SPEC],
            "station_tuning": [PatchType.STATION_SPEC],
        }

        target_types: List[PatchType] = []
        for pt_str in self.config.patch_types:
            target_types.extend(type_mapping.get(pt_str, []))

        # Generate patches from wisdom artifacts
        patches = generate_evolution_patch(wisdom_dir, run_id=run_id)

        for patch in patches:
            if patch.patch_type not in target_types:
                continue

            result.patches_processed += 1

            # Check if already applied or rejected
            applied_marker = wisdom_dir / f".applied_{patch.id}"
            rejected_marker = wisdom_dir / f".rejected_{patch.id}"

            if applied_marker.exists() or rejected_marker.exists():
                result.patches_skipped += 1
                continue

            # Create suggestion record
            suggestion = EvolutionSuggestion(
                patch_id=patch.id,
                target_file=patch.target_file,
                patch_type=patch.patch_type.value,
                reasoning=patch.reasoning,
                confidence=patch.confidence.value,
                risk=patch.risk,
                action_taken="suggested",
                source_run_id=run_id,
            )

            # Validate patch
            validation = validate_evolution_patch(patch, repo_root=repo_root)

            # Determine if we should apply based on policy
            should_apply = False

            if policy == EvolutionApplyPolicy.AUTO_APPLY_ALL:
                should_apply = validation.valid
            elif policy == EvolutionApplyPolicy.AUTO_APPLY_SAFE:
                # Safe mode: only apply low-risk, high-confidence patches
                # that don't require human review
                is_safe = (
                    patch.risk == "low"
                    and patch.confidence.value == "high"
                    and not patch.human_review_required
                )
                should_apply = validation.valid and is_safe
            # SUGGEST_ONLY: should_apply remains False

            if not validation.valid:
                self._handle_rejected_patch(
                    patch=patch,
                    suggestion=suggestion,
                    result=result,
                    wisdom_dir=wisdom_dir,
                    run_id=run_id,
                    policy=policy,
                    errors=validation.errors,
                )
                continue

            if not should_apply:
                self._handle_suggested_patch(
                    patch=patch,
                    suggestion=suggestion,
                    result=result,
                    wisdom_dir=wisdom_dir,
                    run_id=run_id,
                    policy=policy,
                    boundary=boundary,
                )
                continue

            # Apply the patch
            self._apply_patch(
                patch=patch,
                suggestion=suggestion,
                result=result,
                wisdom_dir=wisdom_dir,
                run_id=run_id,
                policy=policy,
                boundary=boundary,
                apply_func=apply_evolution_patch,
            )

        # Write evolution summary to artifacts
        self._write_summary(run_id, result, wisdom_dir, policy, boundary)

        # Emit evolution processing completed event
        self._emit(
            run_id=run_id,
            event_kind="evolution_processing_completed",
            flow_key="wisdom",
            payload={
                "policy": policy.value,
                "boundary": boundary,
                "patches_processed": result.patches_processed,
                "patches_applied": result.patches_applied,
                "patches_suggested": result.patches_suggested,
                "patches_rejected": result.patches_rejected,
                "patches_skipped": result.patches_skipped,
                "applied_patch_ids": result.applied_patch_ids,
            },
        )

        logger.info(
            "Evolution processing completed for run %s: "
            "%d processed, %d applied, %d suggested, %d rejected, %d skipped",
            run_id,
            result.patches_processed,
            result.patches_applied,
            result.patches_suggested,
            result.patches_rejected,
            result.patches_skipped,
        )

        return result

    def _emit(
        self,
        run_id: str,
        event_kind: str,
        flow_key: str,
        payload: Dict[str, Any],
    ) -> None:
        """Emit an event through the configured emitter."""
        if self._event_emitter:
            self._event_emitter.emit(run_id, event_kind, flow_key, payload)

    def _handle_rejected_patch(
        self,
        patch: Any,
        suggestion: EvolutionSuggestion,
        result: EvolutionResult,
        wisdom_dir: Path,
        run_id: str,
        policy: EvolutionApplyPolicy,
        errors: List[str],
    ) -> None:
        """Handle a rejected patch."""
        suggestion.action_taken = "rejected"
        suggestion.rejection_reason = "; ".join(errors)
        result.patches_rejected += 1
        result.rejected_patch_ids.append(
            {
                "patch_id": patch.id,
                "reason": "; ".join(errors),
            }
        )

        # Write rejection marker
        rejected_marker = wisdom_dir / f".rejected_{patch.id}"
        rejected_marker.write_text(
            json.dumps(
                {
                    "rejected_at": datetime.now(timezone.utc).isoformat(),
                    "patch_id": patch.id,
                    "reason": "; ".join(errors),
                    "policy": policy.value,
                    "auto_rejected": True,
                }
            )
        )

        # Emit evolution_rejected event
        self._emit(
            run_id=run_id,
            event_kind="evolution_rejected",
            flow_key="wisdom",
            payload={
                "patch_id": patch.id,
                "target_file": patch.target_file,
                "patch_type": patch.patch_type.value,
                "reason": "; ".join(errors),
                "policy": policy.value,
            },
        )
        result.suggestions.append(suggestion)

    def _handle_suggested_patch(
        self,
        patch: Any,
        suggestion: EvolutionSuggestion,
        result: EvolutionResult,
        wisdom_dir: Path,
        run_id: str,
        policy: EvolutionApplyPolicy,
        boundary: str,
    ) -> None:
        """Handle a suggested (but not applied) patch."""
        result.patches_suggested += 1

        # Write suggestion marker for tracking
        suggestion_marker = wisdom_dir / f".suggested_{patch.id}"
        suggestion_marker.write_text(
            json.dumps(
                {
                    "suggested_at": datetime.now(timezone.utc).isoformat(),
                    "patch_id": patch.id,
                    "target_file": patch.target_file,
                    "reasoning": patch.reasoning,
                    "confidence": patch.confidence.value,
                    "risk": patch.risk,
                    "policy": policy.value,
                    "boundary": boundary,
                }
            )
        )

        # Emit evolution_suggested event (not applied, just recorded)
        self._emit(
            run_id=run_id,
            event_kind="evolution_suggested",
            flow_key="wisdom",
            payload={
                "patch_id": patch.id,
                "target_file": patch.target_file,
                "patch_type": patch.patch_type.value,
                "reasoning": patch.reasoning,
                "confidence": patch.confidence.value,
                "risk": patch.risk,
                "policy": policy.value,
                "boundary": boundary,
            },
        )

        logger.info(
            "Evolution suggestion recorded: %s for %s (policy: %s)",
            patch.id,
            patch.target_file,
            policy.value,
        )
        result.suggestions.append(suggestion)

    def _apply_patch(
        self,
        patch: Any,
        suggestion: EvolutionSuggestion,
        result: EvolutionResult,
        wisdom_dir: Path,
        run_id: str,
        policy: EvolutionApplyPolicy,
        boundary: str,
        apply_func: Any,
    ) -> None:
        """Apply an evolution patch."""
        try:
            apply_result = apply_func(
                patch,
                dry_run=False,
                repo_root=self.config.repo_root,
                create_backup=True,
            )

            if apply_result.success:
                now = datetime.now(timezone.utc)
                suggestion.action_taken = "applied"
                suggestion.applied_at = now.isoformat()

                result.patches_applied += 1
                result.applied_patch_ids.append(patch.id)

                # Write applied marker
                applied_marker = wisdom_dir / f".applied_{patch.id}"
                applied_marker.write_text(
                    json.dumps(
                        {
                            "applied_at": now.isoformat(),
                            "patch_id": patch.id,
                            "changes_made": apply_result.changes_made,
                            "backup_path": apply_result.backup_path,
                            "policy": policy.value,
                            "boundary": boundary,
                            "auto_applied": True,
                        }
                    )
                )

                # Emit evolution_applied event
                self._emit(
                    run_id=run_id,
                    event_kind="evolution_applied",
                    flow_key="wisdom",
                    payload={
                        "patch_id": patch.id,
                        "target_file": patch.target_file,
                        "patch_type": patch.patch_type.value,
                        "changes_made": apply_result.changes_made,
                        "backup_path": apply_result.backup_path,
                        "policy": policy.value,
                        "boundary": boundary,
                    },
                )

                logger.info(
                    "Evolution applied: %s to %s (policy: %s)",
                    patch.id,
                    patch.target_file,
                    policy.value,
                )
            else:
                suggestion.action_taken = "rejected"
                suggestion.rejection_reason = "; ".join(apply_result.errors)
                result.patches_rejected += 1
                result.rejected_patch_ids.append(
                    {
                        "patch_id": patch.id,
                        "reason": "; ".join(apply_result.errors),
                    }
                )

                # Emit evolution_rejected event
                self._emit(
                    run_id=run_id,
                    event_kind="evolution_rejected",
                    flow_key="wisdom",
                    payload={
                        "patch_id": patch.id,
                        "target_file": patch.target_file,
                        "reason": "; ".join(apply_result.errors),
                        "policy": policy.value,
                    },
                )

            result.suggestions.append(suggestion)

        except Exception as e:
            logger.error(
                "Failed to apply evolution patch %s: %s",
                patch.id,
                e,
            )
            suggestion.action_taken = "rejected"
            suggestion.rejection_reason = f"Application failed: {e}"
            result.patches_rejected += 1
            result.rejected_patch_ids.append(
                {
                    "patch_id": patch.id,
                    "reason": f"Application failed: {e}",
                }
            )
            result.suggestions.append(suggestion)

    def _write_summary(
        self,
        run_id: str,
        result: EvolutionResult,
        wisdom_dir: Path,
        policy: EvolutionApplyPolicy,
        boundary: str,
    ) -> None:
        """Write evolution summary to run artifacts.

        Creates an evolution_summary.json file in the wisdom directory
        that records all suggestions, whether applied or not.
        """
        summary = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy": policy.value,
            "boundary": boundary,
            "summary": {
                "patches_processed": result.patches_processed,
                "patches_applied": result.patches_applied,
                "patches_suggested": result.patches_suggested,
                "patches_rejected": result.patches_rejected,
                "patches_skipped": result.patches_skipped,
            },
            "applied_patch_ids": result.applied_patch_ids,
            "rejected_patch_ids": result.rejected_patch_ids,
            "suggestions": [s.to_dict() for s in result.suggestions],
        }

        summary_path = wisdom_dir / "evolution_summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(
            "Evolution summary written to %s",
            summary_path,
        )


# =============================================================================
# Convenience Functions
# =============================================================================


def process_evolution_at_boundary(
    wisdom_dir: Path,
    run_id: str,
    policy: EvolutionApplyPolicy = EvolutionApplyPolicy.SUGGEST_ONLY,
    boundary: str = "run_end",
    patch_types: Optional[List[str]] = None,
    repo_root: Optional[Path] = None,
    emit_events: bool = True,
) -> EvolutionResult:
    """Process evolution patches at a flow or run boundary.

    Convenience function that creates a processor and processes patches.

    Args:
        wisdom_dir: Path to the wisdom directory containing evolution artifacts.
        run_id: The run identifier for event emission.
        policy: Policy controlling evolution patch application.
        boundary: The boundary type ("flow_end" or "run_end").
        patch_types: List of patch types to process.
        repo_root: Repository root path for applying patches.
        emit_events: Whether to emit events.

    Returns:
        EvolutionResult with summary of processed patches.
    """
    config = EvolutionConfig(
        policy=policy,
        boundary=EvolutionBoundary(boundary) if boundary in ("run_end", "flow_end") else EvolutionBoundary.RUN_END,
        patch_types=patch_types or ["flow_evolution", "station_tuning"],
        repo_root=repo_root,
        emit_events=emit_events,
    )

    processor = EvolutionProcessor(config)
    return processor.process(wisdom_dir, run_id, boundary)


__all__ = [
    "EvolutionApplyPolicy",
    "EvolutionBoundary",
    "EvolutionConfig",
    "EvolutionProcessor",
    "EvolutionResult",
    "EvolutionSuggestion",
    "EventEmitter",
    "StorageEventEmitter",
    "process_evolution_at_boundary",
]
