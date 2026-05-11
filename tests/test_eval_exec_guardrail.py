from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [
    REPO_ROOT / "swarm",
    REPO_ROOT / "packages" / "selftest-core" / "src",
]
PATTERN = re.compile(r"\b(eval|exec)\s*\(")

# If you ever must allow a specific file, add its repo-relative posix path here.
ALLOWLIST: set[str] = set()


def test_no_eval_exec_in_production_code() -> None:
    hits: list[str] = []
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel in ALLOWLIST:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for m in PATTERN.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{rel}:{line}")
    assert not hits, "eval() and exec() are forbidden in production code:\n" + "\n".join(hits)
