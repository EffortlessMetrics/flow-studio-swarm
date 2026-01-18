from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def create_run_service(repo_root: Path) -> Optional[Any]:
    try:
        from swarm.runtime.service import RunService
    except ImportError:
        return None

    try:
        return RunService.get_instance(repo_root)
    except Exception:
        return None


def summarize_runs(summaries: Sequence[Any]) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    for summary in summaries:
        if "example" in summary.tags:
            run_type = "example"
        else:
            run_type = "active"

        run_data: Dict[str, Any] = {
            "run_id": summary.id,
            "run_type": run_type,
            "path": summary.path or "",
        }

        if summary.title:
            run_data["title"] = summary.title
        if summary.description:
            run_data["description"] = summary.description
        if summary.spec and summary.spec.backend:
            run_data["backend"] = summary.spec.backend
        if summary.is_exemplar:
            run_data["is_exemplar"] = True

        filtered_tags = [t for t in summary.tags if t not in ("example", "legacy")]
        if filtered_tags:
            run_data["tags"] = filtered_tags

        runs.append(run_data)

    return runs


def list_runs(run_service: Any) -> List[Dict[str, Any]]:
    summaries = run_service.list_runs(
        include_legacy=True,
        include_examples=True,
    )
    return summarize_runs(summaries)


def list_backends(run_service: Any) -> List[Dict[str, Any]]:
    backends = run_service.list_backends()
    return [
        {
            "id": b.id,
            "label": b.label,
            "supports_streaming": b.supports_streaming,
            "supports_events": b.supports_events,
            "supports_cancel": b.supports_cancel,
            "supports_replay": b.supports_replay,
        }
        for b in backends
    ]


def start_run(run_service: Any, flows: List[str], profile_id: Optional[str], backend: str) -> str:
    from swarm.runtime.types import RunSpec

    spec = RunSpec(
        flow_keys=flows,
        profile_id=profile_id,
        backend=backend,
        initiator="flow-studio",
    )
    return run_service.start_run(spec)


def get_events(run_service: Any, run_id: str) -> List[Dict[str, Any]]:
    events = run_service.get_events(run_id)
    return [
        {
            "run_id": e.run_id,
            "ts": e.ts.isoformat() if e.ts else None,
            "kind": e.kind,
            "flow_key": e.flow_key,
            "step_id": e.step_id,
            "agent_key": e.agent_key,
            "payload": e.payload,
        }
        for e in events
    ]


def cancel_run(run_service: Any, run_id: str) -> bool:
    return bool(run_service.cancel_run(run_id))


def mark_exemplar(run_service: Any, run_id: str, is_exemplar: bool) -> bool:
    return bool(run_service.mark_exemplar(run_id, is_exemplar))


def list_exemplars(run_service: Any) -> List[Dict[str, Any]]:
    from swarm.runtime.types import run_summary_to_dict

    exemplars = run_service.list_exemplars()
    return [run_summary_to_dict(s) for s in exemplars]
