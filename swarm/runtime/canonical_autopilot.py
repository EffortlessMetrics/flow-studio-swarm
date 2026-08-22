"""Canonical API-facing autopilot controller.

The legacy controller owns useful macro-flow behavior but initialized only an
in-memory cursor plus a partial run directory. This subclass preserves that
behavior while routing creation through the constitutional run initializer and
allowing callers such as issue intake to supply the one run identity.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import storage
from .autopilot import AutopilotConfig, AutopilotController, AutopilotState
from .run_factory import initialize_run
from .types import RunEvent, RunId, RunSpec, generate_run_id


class CanonicalAutopilotController(AutopilotController):
    """Autopilot whose start boundary creates one complete durable run."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        orchestrator: Optional[Any] = None,
        default_config: Optional[AutopilotConfig] = None,
    ) -> None:
        """Bind API autopilot to the server's configured repository root."""
        if repo_root is None:
            try:
                from swarm.api.server import get_spec_manager

                repo_root = get_spec_manager().repo_root
            except (ImportError, RuntimeError):
                # Standalone and unit-test use can still rely on the legacy
                # controller's deterministic repository-root detection.
                repo_root = None
        super().__init__(
            repo_root=repo_root,
            orchestrator=orchestrator,
            default_config=default_config,
        )

    def start(
        self,
        issue_ref: Optional[str] = None,
        flow_keys: Optional[List[str]] = None,
        profile_id: Optional[str] = None,
        backend: str = "claude-step-orchestrator",
        initiator: str = "autopilot",
        params: Optional[Dict[str, Any]] = None,
        auto_apply_wisdom: Optional[bool] = None,
        auto_apply_policy: Optional[str] = None,
        auto_apply_patch_types: Optional[List[str]] = None,
        run_id: Optional[RunId] = None,
    ) -> RunId:
        """Create a durable autopilot run under a caller-supplied identity."""
        canonical_run_id = run_id or generate_run_id()
        flows = list(flow_keys or self._get_sdlc_flows())
        if not flows:
            raise ValueError("Autopilot requires at least one flow")

        config = AutopilotConfig(
            auto_apply_wisdom=(
                auto_apply_wisdom
                if auto_apply_wisdom is not None
                else self._default_config.auto_apply_wisdom
            ),
            auto_apply_policy=(
                auto_apply_policy
                if auto_apply_policy is not None
                else self._default_config.auto_apply_policy
            ),
            auto_apply_patch_types=list(
                auto_apply_patch_types
                if auto_apply_patch_types is not None
                else self._default_config.auto_apply_patch_types
            ),
        )

        spec = RunSpec(
            flow_keys=flows,
            profile_id=profile_id,
            backend=backend,
            initiator=initiator,
            params={
                **(params or {}),
                "autopilot": True,
                "issue_ref": issue_ref,
                "auto_apply_wisdom": config.auto_apply_wisdom,
                "auto_apply_policy": config.auto_apply_policy,
            },
            no_human_mid_flow=True,
        )
        state = AutopilotState(
            run_id=canonical_run_id,
            spec=spec,
            config=config,
            flows_to_execute=flows,
            current_flow_index=0,
        )

        runs_dir = self._repo_root / "swarm" / "runs"
        initialize_run(
            canonical_run_id,
            spec,
            flow_key=flows[0],
            mode="execute",
            runs_dir=runs_dir,
        )
        self._states[canonical_run_id] = state

        storage.append_event(
            canonical_run_id,
            RunEvent(
                run_id=canonical_run_id,
                ts=datetime.now(timezone.utc),
                kind="autopilot_started",
                flow_key=flows[0],
                payload={
                    "flows": flows,
                    "issue_ref": issue_ref,
                    "no_human_mid_flow": True,
                },
            ),
            runs_dir,
        )

        return canonical_run_id
