from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def load_tours(repo_root: Path) -> Dict[str, Any]:
    """Load tours from swarm/config/tours/*.yaml"""
    import yaml

    tours: Dict[str, Any] = {}
    tours_dir = repo_root / "swarm" / "config" / "tours"

    if not tours_dir.exists():
        return tours

    for cfg_path in sorted(tours_dir.glob("*.yaml")):
        try:
            text = cfg_path.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
            if data is None or not isinstance(data, dict):
                continue
            tour_id = data.get("id")
            if not tour_id:
                continue

            tour_steps = []
            for raw_step in data.get("steps") or []:
                if not isinstance(raw_step, dict):
                    continue
                target = raw_step.get("target") or {}
                tour_steps.append({
                    "target_type": target.get("type", "flow"),
                    "target_flow": target.get("flow", ""),
                    "target_step": target.get("step", ""),
                    "title": raw_step.get("title", ""),
                    "text": raw_step.get("text", ""),
                    "action": raw_step.get("action", "select_flow"),
                })

            tours[tour_id] = {
                "id": tour_id,
                "title": data.get("title", tour_id),
                "description": (data.get("description") or "").strip(),
                "steps": tour_steps,
            }
        except Exception:
            continue

    return tours
