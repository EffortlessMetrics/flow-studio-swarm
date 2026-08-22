"""Create one canonical Flow Studio run from an issue snapshot."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from swarm.runtime.safe_paths import validate_path_component

from ..services.run_state import get_state_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["issues"])


class IssueIngestionRequest(BaseModel):
    provider: str = Field("github", description="Issue provider")
    repo: Optional[str] = Field(None, description="Repository as owner/repo")
    issue_number: Optional[int] = None
    issue_url: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    labels: Optional[List[str]] = None
    start_autopilot: bool = False
    flow_keys: Optional[List[str]] = None


class IssueIngestionResponse(BaseModel):
    run_id: str
    status: str
    issue_snapshot_path: str
    autopilot_started: bool = False
    events_url: str
    created_at: str


class IssueSnapshot(BaseModel):
    provider: str
    repo: str
    issue_number: int
    title: str
    body: str
    labels: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    fetched_at: str
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


def _parse_issue_url(url: str) -> tuple[str, str, int]:
    github_match = re.match(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)", url)
    if github_match:
        return "github", github_match.group(1), int(github_match.group(2))

    gitlab_match = re.match(r"https?://gitlab\.com/([^/]+/[^/]+)/-/issues/(\d+)", url)
    if gitlab_match:
        return "gitlab", gitlab_match.group(1), int(gitlab_match.group(2))

    raise ValueError(f"Unrecognized issue URL format: {url}")


def _get_autopilot_controller():
    from .autopilot_routes import _get_autopilot_controller as get_controller

    return get_controller()


def _issue_run_id(repo: Optional[str], issue_number: Optional[int], now: datetime) -> str:
    repo_component = (repo or "local/manual").replace("/", "-")
    return f"issue-{repo_component}-{issue_number or 0}-{now.strftime('%Y%m%d%H%M%S')}"


@router.post("/from-issue", response_model=IssueIngestionResponse, status_code=201)
async def ingest_issue(request: IssueIngestionRequest):
    """Snapshot an issue and optionally start autopilot under the same run ID."""
    try:
        provider = request.provider
        repo = request.repo
        issue_number = request.issue_number

        if request.issue_url:
            try:
                provider, repo, issue_number = _parse_issue_url(request.issue_url)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_url",
                        "message": str(exc),
                        "details": {"url": request.issue_url},
                    },
                ) from exc

        if (not repo or issue_number is None) and not request.title:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "missing_reference",
                    "message": "Provide repo+issue_number, issue_url, or title+body",
                    "details": {},
                },
            )

        now = datetime.now(timezone.utc)
        issue_ref = f"{repo}#{issue_number}" if repo and issue_number is not None else None
        issue_url = request.issue_url
        if not issue_url and provider == "github" and repo and issue_number is not None:
            issue_url = f"https://github.com/{repo}/issues/{issue_number}"

        snapshot = IssueSnapshot(
            provider=provider,
            repo=repo or "local/manual",
            issue_number=issue_number or 0,
            title=request.title or f"Issue #{issue_number}",
            body=request.body or "",
            labels=request.labels or [],
            url=issue_url,
            fetched_at=now.isoformat(),
            source_metadata={"ingested_via": "api", "provider": provider},
        )

        run_id = _issue_run_id(repo, issue_number, now)
        try:
            validate_path_component(run_id, "generated run_id")
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_run_id",
                    "message": f"Generated run ID is invalid: {exc}",
                    "details": {"run_id": run_id},
                },
            ) from exc

        state_manager = get_state_manager()
        snapshot_relative = Path("signal") / "issue_snapshot.json"
        context = {
            "issue_ref": issue_ref or "manual",
            "issue_snapshot_path": snapshot_relative.as_posix(),
        }

        autopilot_started = False
        if request.start_autopilot:
            controller = _get_autopilot_controller()
            started_run_id = controller.start(
                run_id=run_id,
                issue_ref=issue_ref,
                flow_keys=request.flow_keys,
                initiator="api:issue",
                params={"issue_snapshot_path": snapshot_relative.as_posix()},
            )
            if started_run_id != run_id:
                raise RuntimeError(
                    f"Autopilot changed canonical run identity: {run_id} -> {started_run_id}"
                )
            autopilot_started = True

            # Test doubles and compatibility controllers may not yet initialize
            # the durable state. Real canonical autopilot already has.
            try:
                await state_manager.get_run(run_id)
            except FileNotFoundError:
                await state_manager.create_run(
                    flow_id=(request.flow_keys or ["signal"])[0],
                    run_id=run_id,
                    context=context,
                    mode="execute",
                    initiator="api:issue",
                )
        else:
            await state_manager.create_run(
                flow_id="signal",
                run_id=run_id,
                context=context,
                mode="execute",
                initiator="api:issue",
            )

        run_dir = state_manager.runs_root / run_id
        signal_dir = run_dir / "signal"
        signal_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = signal_dir / "issue_snapshot.json"
        snapshot_path.write_text(
            json.dumps(snapshot.model_dump(), indent=2),
            encoding="utf-8",
        )
        (signal_dir / "issue.md").write_text(
            f"# {snapshot.title}\n\n"
            f"**Source:** {snapshot.url or 'Manual input'}\n"
            f"**Labels:** {', '.join(snapshot.labels) if snapshot.labels else 'None'}\n\n"
            f"---\n\n{snapshot.body}\n",
            encoding="utf-8",
        )

        return IssueIngestionResponse(
            run_id=run_id,
            status="created",
            issue_snapshot_path=snapshot_relative.as_posix(),
            autopilot_started=autopilot_started,
            events_url=f"/api/runs/{run_id}/events",
            created_at=now.isoformat(),
        )
    except HTTPException:
        raise
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to ingest issue")
        raise HTTPException(
            status_code=500,
            detail={"error": "ingestion_failed", "message": str(exc), "details": {}},
        ) from exc
