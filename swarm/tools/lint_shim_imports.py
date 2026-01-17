#!/usr/bin/env python3
"""Guardrail: prevent new imports of deprecated shim modules."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


SHIM_PATTERNS = [
    "swarm.runtime.router",
    "swarm.config.pack_registry",
    "swarm.runtime.db",
    "swarm.spec.compiler_legacy",
]


def _run_git(repo_root: Path, args: List[str]) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None

    if result.returncode != 0:
        return None
    return result.stdout


def _get_repo_root() -> Path:
    root = _run_git(Path.cwd(), ["rev-parse", "--show-toplevel"])
    if root:
        return Path(root.strip())
    return Path.cwd()


def _detect_base_ref(repo_root: Path, explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit

    candidates = [
        "origin/main",
        "origin/master",
        "main",
        "master",
    ]
    for ref in candidates:
        if _run_git(repo_root, ["rev-parse", "--verify", ref]):
            return ref
    return None


def _diff_text(repo_root: Path, base_ref: Optional[str]) -> str:
    if base_ref:
        merge_base = _run_git(repo_root, ["merge-base", "HEAD", base_ref])
        if merge_base:
            diff = _run_git(
                repo_root,
                ["diff", "--no-color", "--unified=0", f"{merge_base.strip()}...HEAD"],
            )
            if diff is not None:
                return diff

    diff = _run_git(repo_root, ["diff", "--no-color", "--unified=0", "HEAD"])
    return diff or ""


def _iter_added_lines(diff_text: str) -> Iterable[Tuple[str, str]]:
    current_file: Optional[str] = None
    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ "):
            path = raw_line[4:].strip()
            if path == "/dev/null":
                current_file = None
                continue
            if path.startswith("b/"):
                path = path[2:]
            current_file = path
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            if current_file:
                yield current_file, raw_line[1:]


def _find_new_shim_imports(diff_text: str) -> List[str]:
    violations: List[str] = []
    for path, line in _iter_added_lines(diff_text):
        if not path.endswith(".py"):
            continue
        for pattern in SHIM_PATTERNS:
            if pattern in line:
                violations.append(f"{path}: {line.strip()}")
                break
    return violations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        help="Git ref to diff against (defaults to origin/main/main/master if available).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = _get_repo_root()
    base_ref = _detect_base_ref(repo_root, args.base)
    diff_text = _diff_text(repo_root, base_ref)

    if not diff_text.strip():
        print("No changes detected for shim import guard.")
        return 0

    violations = _find_new_shim_imports(diff_text)
    if not violations:
        print("Shim import guard passed (no new shim imports).")
        return 0

    print("Shim import guard failed. New shim imports detected:")
    for violation in violations:
        print(f"- {violation}")
    print("Avoid adding new shim imports; migrate to canonical modules instead.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
