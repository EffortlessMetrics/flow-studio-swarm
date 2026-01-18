from __future__ import annotations

import logging
from collections import deque
from pathlib import Path
import re

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


def check_ui_assets(ui_dir: Path, strict: bool) -> None:
    """
    Check for required compiled JS files at startup.

    This check is drift-proof: instead of a hardcoded list of all modules,
    we require only entrypoints (main.js, flow-studio-app.js) and walk the
    full import graph (BFS) to detect missing dependencies automatically.

    Supported import patterns:
      - Static: import ... from "./x.js" or "../x.js"
      - Side-effect: import "./x.js" or "../x.js"
      - Dynamic: import("./x.js") or import("../x.js")

    The graph walk catches transitive dependencies, e.g.:
      - flow-studio-app.js imports ./runs_flows.js (exists)
      - runs_flows.js imports ../utils/foo.js (missing)
      - This check will catch utils/foo.js as missing

    Path traversal protection: imports that escape the js/ directory are
    flagged as errors (e.g., importing "../../secrets.js").

    Args:
        ui_dir: Path to the flow_studio_ui directory
        strict: When True, missing assets raise RuntimeError

    Raises:
        RuntimeError: If strict is True and files are missing
    """
    js_dir = ui_dir / "js"

    if not js_dir.exists():
        msg = f"Flow Studio JS directory not found: {js_dir}. Run `make ts-build`."
        if strict:
            logger.error(msg)
            raise RuntimeError(msg)
        logger.warning(msg)
        return

    # Only require entrypoints - everything else is derived from imports
    entrypoints = ["main.js", "flow-studio-app.js"]
    missing_entrypoints = [f for f in entrypoints if not (js_dir / f).exists()]

    if missing_entrypoints:
        msg = (
            "Missing Flow Studio entrypoints: "
            + ", ".join(missing_entrypoints)
            + ". Run `make ts-build`."
        )
        if strict:
            logger.error(msg)
            raise RuntimeError(msg)
        logger.warning(msg)
        return

    import_export_from_re = re.compile(
        r'^\s*(?:import|export)\b.*?\bfrom\s*["\'](\.?\.?/[^"\']+)["\']',
        re.MULTILINE,
    )
    side_effect_re = re.compile(r'^\s*import\s*["\'](\.?\.?/[^"\']+)["\']', re.MULTILINE)
    dynamic_re = re.compile(r'\bimport\(\s*["\'](\.?\.?/[^"\']+)["\']\s*\)')

    def parse_imports(text: str) -> set[str]:
        return (
            set(import_export_from_re.findall(text))
            | set(side_effect_re.findall(text))
            | set(dynamic_re.findall(text))
        )

    js_root = js_dir.resolve()
    queue: deque[Path] = deque(Path(ep) for ep in entrypoints)
    seen: set[str] = {ep for ep in entrypoints}
    missing: list[str] = []

    while queue:
        rel = queue.popleft()
        path = js_dir / rel
        if not path.exists():
            missing.append(rel.as_posix())
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Failed to read %s: %s", rel, e)
            continue

        for spec in parse_imports(text):
            dep_abs = (path.parent / spec).resolve(strict=False)

            try:
                dep_rel = dep_abs.relative_to(js_root).as_posix()
            except ValueError:
                missing.append(f"{rel} -> {spec} (escapes js/)")
                continue

            if dep_rel not in seen:
                seen.add(dep_rel)
                queue.append(Path(dep_rel))

    if missing:
        msg = (
            "Missing compiled Flow Studio module dependencies: "
            + ", ".join(sorted(set(missing)))
            + ". Run `make ts-build`."
        )
        if strict:
            logger.error(msg)
            raise RuntimeError(msg)
        logger.warning(msg)


def mount_static(app: FastAPI, ui_dir: Path) -> None:
    if (ui_dir / "css").exists():
        app.mount("/css", StaticFiles(directory=str(ui_dir / "css")), name="css")
    if (ui_dir / "js").exists():
        app.mount("/js", StaticFiles(directory=str(ui_dir / "js")), name="js")
    if (ui_dir / "static").exists():
        app.mount("/static", StaticFiles(directory=str(ui_dir / "static")), name="static")
