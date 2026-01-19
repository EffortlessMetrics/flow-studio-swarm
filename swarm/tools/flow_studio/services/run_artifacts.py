from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from swarm.runtime.safe_paths import validate_path_component


class RunArtifactsError(Exception):
    def __init__(self, status_code: int, payload: Dict[str, Any]):
        super().__init__(payload.get("error", "Run artifacts error"))
        self.status_code = status_code
        self.payload = payload


def resolve_run_path(run_id: str, run_inspector: Optional[Any]) -> Path:
    validate_path_component(run_id, "run_id")

    run_path = None
    if run_inspector is not None:
        run_path = run_inspector.get_run_path(run_id)

    if run_path is None:
        from swarm.runtime import storage as runtime_storage
        run_path = runtime_storage.find_run_path(run_id)

    if run_path is None:
        raise RunArtifactsError(404, {"error": f"Run '{run_id}' not found"})

    return Path(run_path)


def load_transcript(run_id: str, flow_key: str, step_id: str, run_inspector: Optional[Any]) -> Dict[str, Any]:
    validate_path_component(flow_key, "flow_key")
    validate_path_component(step_id, "step_id")
    run_path = resolve_run_path(run_id, run_inspector)

    llm_dir = run_path / flow_key / "llm"
    if not llm_dir.exists():
        raise RunArtifactsError(
            404,
            {
                "error": "No transcripts available for this step",
                "hint": "Transcripts are written by Claude flows using record_event.py",
            },
        )

    transcripts = list(llm_dir.glob(f"{step_id}-*.jsonl"))
    if not transcripts:
        raise RunArtifactsError(
            404,
            {
                "error": f"No transcript found for step '{step_id}'",
                "available_files": [f.name for f in llm_dir.glob("*.jsonl")],
            },
        )

    transcript_file = transcripts[0]
    messages = []
    engine = None

    try:
        with transcript_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue

        parts = transcript_file.stem.split("-")
        if len(parts) >= 3:
            engine = parts[-1]
    except Exception as exc:
        raise RunArtifactsError(500, {"error": f"Failed to read transcript: {str(exc)}"})

    return {
        "run_id": run_id,
        "flow_key": flow_key,
        "step_id": step_id,
        "engine": engine,
        "messages": messages,
        "transcript_file": transcript_file.name,
    }


def load_receipt(run_id: str, flow_key: str, step_id: str, run_inspector: Optional[Any]) -> Dict[str, Any]:
    validate_path_component(flow_key, "flow_key")
    validate_path_component(step_id, "step_id")
    run_path = resolve_run_path(run_id, run_inspector)

    receipts_dir = run_path / flow_key / "receipts"
    if not receipts_dir.exists():
        raise RunArtifactsError(404, {"error": "No receipts available for this step"})

    receipts = list(receipts_dir.glob(f"{step_id}-*.json"))
    if not receipts:
        raise RunArtifactsError(
            404,
            {
                "error": f"No receipt found for step '{step_id}'",
                "available_files": [f.name for f in receipts_dir.glob("*.json")],
            },
        )

    receipt_file = receipts[0]

    try:
        with receipt_file.open("r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except Exception as exc:
        raise RunArtifactsError(500, {"error": f"Failed to read receipt: {str(exc)}"})

    return {
        "run_id": run_id,
        "flow_key": flow_key,
        "step_id": step_id,
        "receipt": receipt,
        "receipt_file": receipt_file.name,
    }


def load_wisdom_summary(run_id: str, run_inspector: Optional[Any]) -> Dict[str, Any]:
    run_path = resolve_run_path(run_id, run_inspector)

    wisdom_summary_path = run_path / "wisdom" / "wisdom_summary.json"
    if not wisdom_summary_path.exists():
        raise RunArtifactsError(
            404,
            {
                "error": "No wisdom summary available for this run",
                "hint": f"Generate with: uv run swarm/tools/wisdom_summarizer.py {run_id}",
            },
        )

    try:
        with wisdom_summary_path.open("r", encoding="utf-8") as handle:
            summary = json.load(handle)
        return summary
    except Exception as exc:
        raise RunArtifactsError(
            500,
            {"error": f"Failed to read wisdom summary: {str(exc)}"},
        )
