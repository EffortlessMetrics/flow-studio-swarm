"""
Issue ingestion endpoints for Flow Studio API.

Provides REST endpoints for:
- Creating runs from issue references (GitHub, GitLab, etc.)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.run_state import get_state_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["issues"])


# =============================================================================
# Pydantic Models
# =============================================================================


class IssueIngestionRequest(BaseModel):
    """Request to start a run from an issue."""

    provider: str = Field("github", description="Issue provider (github, gitlab, etc.)")
    repo: Optional[str] = Field(None, description="Repository in 'owner/repo' format")
    issue_number: Optional[int] = Field(None, description="Issue number")
    issue_url: Optional[str] = Field(
        None, description="Full issue URL (alternative to repo+number)"
    )
    title: Optional[str] = Field(None, description="Issue title (if not fetching)")
    body: Optional[str] = Field(None, description="Issue body (if not fetching)")
    labels: Optional[List[str]] = Field(None, description="Issue labels")
    start_autopilot: bool = Field(False, description="Start autopilot run after ingestion")
    flow_keys: Optional[List[str]] = Field(None, description="Flows to execute (defaults to all)")


class IssueIngestionResponse(BaseModel):
    """Response from issue ingestion."""

    run_id: str
    status: str
    issue_snapshot_path: str
    autopilot_started: bool = False
    events_url: str
    created_at: str


class IssueSnapshot(BaseModel):
    """Snapshot of an issue for Flow 1 input."""

    provider: str
    repo: str
    issue_number: int
    title: str
    body: str
    labels: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    fetched_at: str
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Helpers
# =============================================================================


def _parse_issue_url(url: str) -> tuple[str, str, int]:
    """Parse an issue URL into provider, repo, and number.

    Args:
        url: Issue URL (e.g., 'https://github.com/owner/repo/issues/123')

    Returns:
        Tuple of (provider, repo, issue_number)

    Raises:
        ValueError: If URL format is not recognized.
    """
    # GitHub: https://github.com/owner/repo/issues/123
    gh_match = re.match(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)", url)
    if gh_match:
        return "github", gh_match.group(1), int(gh_match.group(2))

    # GitLab: https://gitlab.com/owner/repo/-/issues/123
    gl_match = re.match(r"https?://gitlab\.com/([^/]+/[^/]+)/-/issues/(\d+)", url)
    if gl_match:
        return "gitlab", gl_match.group(1), int(gl_match.group(2))

    raise ValueError(f"Unrecognized issue URL format: {url}")


def _get_autopilot_controller():
    """Get or create the global autopilot controller."""
    from swarm.runtime.autopilot import AutopilotController

    # Import from autopilot_routes to share the same controller instance
    from .autopilot_routes import _get_autopilot_controller as get_controller

    return get_controller()


# =============================================================================
# Issue Ingestion Endpoints
# =============================================================================


@router.post("/from-issue", response_model=IssueIngestionResponse, status_code=201)
async def ingest_issue(request: IssueIngestionRequest):
    """Create a run from an issue reference.

    Writes an issue snapshot to the run's signal/ directory as the canonical
    input artifact for Flow 1 (Signal). Optionally starts an autopilot run.

    The issue can be specified by:
    - repo + issue_number: e.g., "owner/repo" and 123
    - issue_url: e.g., "https://github.com/owner/repo/issues/123"
    - title + body: Manual issue data (no fetching)

    Args:
        request: Issue ingestion request.

    Returns:
        IssueIngestionResponse with run_id and snapshot path.

    Raises:
        400: Invalid issue reference.
        500: Ingestion failed.
    """
    try:
        # Determine issue details
        provider = request.provider
        repo = request.repo
        issue_number = request.issue_number

        if request.issue_url:
            try:
                provider, repo, issue_number = _parse_issue_url(request.issue_url)
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_url",
                        "message": str(e),
                        "details": {"url": request.issue_url},
                    },
                )

        if not repo or issue_number is None:
            if not request.title:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "missing_reference",
                        "message": "Must provide repo+issue_number, issue_url, or title+body",
                        "details": {},
                    },
                )

        # Create issue snapshot
        now = datetime.now(timezone.utc)
        snapshot = IssueSnapshot(
            provider=provider,
            repo=repo or "local/manual",
            issue_number=issue_number or 0,
            title=request.title or f"Issue #{issue_number}",
            body=request.body or "",
            labels=request.labels or [],
            url=request.issue_url
            or (
                f"https://github.com/{repo}/issues/{issue_number}"
                if provider == "github" and repo and issue_number
                else None
            ),
            fetched_at=now.isoformat(),
            source_metadata={
                "ingested_via": "api",
                "provider": provider,
            },
        )

        # Generate run ID
        run_id = f"issue-{repo.replace('/', '-') if repo else 'manual'}-{issue_number or 0}-{now.strftime('%Y%m%d%H%M%S')}"

        # Create run directory structure
        state_manager = get_state_manager()
        run_dir = state_manager.runs_root / run_id
        signal_dir = run_dir / "signal"
        signal_dir.mkdir(parents=True, exist_ok=True)

        # Write issue snapshot
        snapshot_path = signal_dir / "issue_snapshot.json"
        snapshot_path.write_text(
            json.dumps(snapshot.model_dump(), indent=2),
            encoding="utf-8",
        )

        # Also write as markdown for human readability
        issue_md_path = signal_dir / "issue.md"
        issue_md_path.write_text(
            f"# {snapshot.title}\n\n"
            f"**Source:** {snapshot.url or 'Manual input'}\n"
            f"**Labels:** {', '.join(snapshot.labels) if snapshot.labels else 'None'}\n\n"
            f"---\n\n"
            f"{snapshot.body}\n",
            encoding="utf-8",
        )

        # Create initial run state
        await state_manager.create_run(
            flow_id="signal",
            run_id=run_id,
            context={
                "issue_ref": f"{repo}#{issue_number}" if repo else "manual",
                "issue_snapshot_path": str(snapshot_path.relative_to(run_dir)),
            },
        )

        # Optionally start autopilot
        autopilot_started = False
        if request.start_autopilot:
            controller = _get_autopilot_controller()
            controller.start(
                issue_ref=f"{repo}#{issue_number}" if repo else None,
                flow_keys=request.flow_keys,
            )
            autopilot_started = True

        return IssueIngestionResponse(
            run_id=run_id,
            status="created",
            issue_snapshot_path=str(snapshot_path.relative_to(run_dir)),
            autopilot_started=autopilot_started,
            events_url=f"/api/runs/{run_id}/events",
            created_at=now.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to ingest issue: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ingestion_failed",
                "message": str(e),
                "details": {},
            },
        )
