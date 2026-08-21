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
from swarm.api.routes.events import EventType, generate_run_events, write_event_sync
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
    """Read one UTF-8 JSON object from ``path``."""
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    """Read all non-empty JSONL rows from ``path``."""
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _record_run_id(record: dict) -> str | None:
    """Return the canonical identity from runtime or summary-shaped data."""
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

    # RunSpec remains reusable intent scoped by its containing run directory;
    # identity is repeated only where it is semantically part of the record.
    assert spec["flow_keys"] == ["signal"]
    assert spec["backend"] == "claude-step-orchestrator"
    assert _record_run_id(meta) == run_id
    assert _record_run_id(state) == run_id

    assert events, "canonical initialization must append a run_created event"
    first_event = events[0]
    assert first_event["run_id"] == run_id
    assert first_event["kind"] == "run_created"
    assert {"event_id", "seq", "run_id", "kind"} <= first_event.keys()
    assert isinstance(first_event["seq"], int) and first_event["seq"] > 0
    assert isinstance(first_event["event_id"], str) and first_event["event_id"]


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
        """Collect the connection event and first canonical journal event."""
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


def test_control_event_writer_uses_canonical_journal(run_api) -> None:
    """Compatibility control writers may translate names, never schemas."""
    client, manager = run_api
    response = client.post("/api/runs", json={"flow_id": "signal"})
    assert response.status_code == 201
    run_id = response.json()["run_id"]

    write_event_sync(
        run_id,
        manager.runs_root,
        EventType.RUN_STOPPING,
        {"run_id": run_id, "flow_key": "signal", "reason": "contract_test"},
    )

    events = _read_jsonl(manager.runs_root / run_id / "events.jsonl")
    assert events[-1]["kind"] == "run_stopping"
    assert events[-1]["run_id"] == run_id
    assert "event" not in events[-1]
    assert events[-1]["payload"]["reason"] == "contract_test"


def test_issue_ingestion_supplies_one_identity_to_autopilot(
    run_api,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue intake selects the ID and autopilot must preserve it."""
    client, manager = run_api

    class FakeAutopilotController:
        """Record the supplied identity without performing real execution."""

        def __init__(self) -> None:
            """Create an empty invocation ledger."""
            self.start_calls: list[dict] = []

        def start(self, **kwargs) -> str:
            """Return exactly the identity selected by issue intake."""
            self.start_calls.append(kwargs)
            return kwargs["run_id"]

    controller = FakeAutopilotController()
    monkeypatch.setattr(issue_routes, "_get_autopilot_controller", lambda: controller)

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
    assert len(controller.start_calls) == 1

    supplied_run_id = controller.start_calls[0]["run_id"]
    assert payload["run_id"] == supplied_run_id
    assert payload["events_url"] == f"/api/runs/{supplied_run_id}/events"

    run_dir = manager.runs_root / supplied_run_id
    snapshot_path = run_dir / payload["issue_snapshot_path"]
    assert snapshot_path.is_file()
    assert {path.name for path in manager.runs_root.iterdir()} == {supplied_run_id}
    assert {"spec.json", "meta.json", "run_state.json", "events.jsonl"} <= {
        path.name for path in run_dir.iterdir()
    }
