"""Constitutional integration tests for the Flow Studio run spine.

These tests deliberately cross package boundaries. A public execute request must
create one durable run identity, and transport adapters must preserve canonical
event meaning instead of inventing parallel state or event contracts.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import swarm.api.routes.issue_routes as issue_routes
import swarm.api.routes.runs_control as runs_control
import swarm.api.routes.runs_crud as runs_crud
from swarm.api.routes.events import generate_run_events
from swarm.api.routes.runs import router as runs_router
from swarm.api.services.run_state import RunStateManager


@pytest.fixture
def run_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[tuple[TestClient, RunStateManager]]:
    """Mount the public run API against an isolated durable run directory."""
    manager = RunStateManager(tmp_path / "runs")

    monkeypatch.setattr(runs_crud, "get_state_manager", lambda: manager)
    monkeypatch.setattr(runs_control, "get_state_manager", lambda: manager)
    monkeypatch.setattr(issue_routes, "get_state_manager", lambda: manager)

    app = FastAPI()
    app.include_router(runs_router, prefix="/api")

    with TestClient(app) as client:
        yield client, manager


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _record_run_id(record: dict) -> str | None:
    return record.get("run_id") or record.get("id")


def test_execute_start_returns_after_canonical_run_initialization(run_api) -> None:
    """HTTP 201 in execute mode requires one complete durable launch record."""
    client, manager = run_api

    response = client.post(
        "/api/runs",
        json={"flow_id": "signal", "mode": "execute"},
    )

    assert response.status_code == 201
    run_id = response.json()["run_id"]
    run_dir = manager.runs_root / run_id

    required_files = ("spec.json", "meta.json", "run_state.json", "events.jsonl")
    missing = [name for name in required_files if not (run_dir / name).is_file()]
    assert not missing, (
        "POST /api/runs returned 201 for execute mode without a canonical "
        f"durable launch record; missing: {missing}"
    )

    spec = _read_json(run_dir / "spec.json")
    meta = _read_json(run_dir / "meta.json")
    state = _read_json(run_dir / "run_state.json")
    events = _read_jsonl(run_dir / "events.jsonl")

    assert _record_run_id(spec) == run_id
    assert _record_run_id(meta) == run_id
    assert _record_run_id(state) == run_id

    assert events, "canonical initialization must append a run_created event"
    first_event = events[0]
    assert first_event["run_id"] == run_id
    assert first_event["kind"] == "run_created"
    assert {"event_id", "seq", "run_id", "kind"} <= first_event.keys()


def test_sse_preserves_runtime_event_kind(tmp_path: Path) -> None:
    """SSE is a transport projection of RunEvent.kind, not another dialect."""
    runs_root = tmp_path / "runs"
    run_id = "run-sse-contract"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)

    (run_dir / "run_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "flow_key": "signal",
                "status": "running",
                "current_step_id": "intake",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "ts": "2026-08-20T00:00:00Z",
                "kind": "step_start",
                "flow_key": "signal",
                "event_id": "evt-step-start-1",
                "seq": 1,
                "step_id": "intake",
                "agent_key": None,
                "payload": {"step_index": 0},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    async def collect_first_runtime_event() -> tuple[str, str]:
        stream = generate_run_events(
            run_id=run_id,
            runs_root=runs_root,
            poll_interval=0,
            heartbeat_interval=3600,
        )
        try:
            connected = await anext(stream)
            runtime_event = await anext(stream)
            return connected, runtime_event
        finally:
            await stream.aclose()

    connected, runtime_event = asyncio.run(collect_first_runtime_event())

    assert "event: connected\n" in connected
    assert "event: step:started\n" in runtime_event
    assert '"kind": "step_start"' in runtime_event
    assert '"event_id": "evt-step-start-1"' in runtime_event


def test_issue_ingestion_reuses_started_autopilot_run_identity(
    run_api,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue intake and its requested autopilot execution are the same run."""
    client, manager = run_api
    canonical_run_id = "run-issue-autopilot-contract"

    class FakeAutopilotController:
        def __init__(self) -> None:
            self.start_calls: list[dict] = []

        def start(self, **kwargs) -> str:
            self.start_calls.append(kwargs)
            return canonical_run_id

    controller = FakeAutopilotController()
    monkeypatch.setattr(
        issue_routes,
        "_get_autopilot_controller",
        lambda: controller,
    )

    response = client.post(
        "/api/runs/from-issue",
        json={
            "title": "Constitutional run identity",
            "body": "The issue snapshot and execution must share one run ID.",
            "start_autopilot": True,
            "flow_keys": ["signal"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["autopilot_started"] is True
    assert payload["run_id"] == canonical_run_id
    assert payload["events_url"] == f"/api/runs/{canonical_run_id}/events"

    snapshot_path = manager.runs_root / canonical_run_id / payload["issue_snapshot_path"]
    assert snapshot_path.is_file()
    assert {path.name for path in manager.runs_root.iterdir()} == {canonical_run_id}
    assert len(controller.start_calls) == 1
