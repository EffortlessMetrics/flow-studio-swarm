#!/usr/bin/env python3
"""Guardrail: enforce rough complexity thresholds on changed Python files."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


DEFAULT_THRESHOLDS = {
    "line_count": 500,
    "function_count": 20,
    "class_count": 5,
    "cyclomatic_complexity": 50,
}


class FileAnalyzer(ast.NodeVisitor):
    """AST visitor to count functions, classes, and a rough branch proxy."""

    def __init__(self) -> None:
        self.function_count = 0
        self.class_count = 0
        self.cyclomatic_complexity = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_count += 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                self.cyclomatic_complexity += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_count += 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                self.cyclomatic_complexity += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_count += 1
        self.generic_visit(node)


def analyze_file(filepath: Path) -> Optional[Dict[str, int]]:
    """Analyze a Python file and return metrics."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    line_count = len(content.splitlines())

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {
            "line_count": line_count,
            "function_count": 0,
            "class_count": 0,
            "cyclomatic_complexity": 0,
        }

    analyzer = FileAnalyzer()
    analyzer.visit(tree)

    return {
        "line_count": line_count,
        "function_count": analyzer.function_count,
        "class_count": analyzer.class_count,
        "cyclomatic_complexity": analyzer.cyclomatic_complexity,
    }


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
    return result.stdout.strip()


def _get_repo_root() -> Path:
    root = _run_git(Path.cwd(), ["rev-parse", "--show-toplevel"])
    if root:
        return Path(root)
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


def _collect_changed_files(repo_root: Path, base_ref: Optional[str]) -> Set[str]:
    files: Set[str] = set()

    if base_ref:
        merge_base = _run_git(repo_root, ["merge-base", "HEAD", base_ref])
        if merge_base:
            diff = _run_git(repo_root, ["diff", "--name-only", "--diff-filter=AM", f"{merge_base}...HEAD"])
            if diff:
                files.update(line.strip() for line in diff.splitlines() if line.strip())

    for args in (
        ["diff", "--name-only", "--diff-filter=AM"],
        ["diff", "--cached", "--name-only", "--diff-filter=AM"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        output = _run_git(repo_root, args)
        if output:
            files.update(line.strip() for line in output.splitlines() if line.strip())

    return files


def _normalize_path(repo_root: Path, path_str: str) -> Optional[str]:
    path = repo_root / path_str
    if not path.exists():
        return None
    return path.resolve().relative_to(repo_root).as_posix()


def _load_allowlist(path: Path) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    entries: Dict[str, Dict[str, str]] = {}
    errors: List[str] = []

    if not path.exists():
        return entries, errors

    today = dt.date.today()
    lines = path.read_text(encoding="utf-8").splitlines()

    for idx, line in enumerate(lines, start=1):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue

        parts = [part.strip() for part in raw.split("|")]
        if len(parts) != 3:
            errors.append(f"{path}:{idx} invalid format (expected 3 fields).")
            continue

        rel_path, expires_str, reason = parts
        if not rel_path or not expires_str or not reason:
            errors.append(f"{path}:{idx} missing path, expires, or reason.")
            continue

        try:
            expires = dt.date.fromisoformat(expires_str)
        except ValueError:
            errors.append(f"{path}:{idx} invalid expires date: {expires_str}.")
            continue

        if expires < today:
            errors.append(
                f"{path}:{idx} allowlist entry expired ({expires_str}) for {rel_path}."
            )

        entries[rel_path] = {
            "expires": expires_str,
            "reason": reason,
        }

    return entries, errors


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        help="Git ref to diff against (defaults to origin/main/main/master if available).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all Python files instead of only changed files.",
    )
    parser.add_argument(
        "--allowlist",
        default=str(Path(__file__).with_name("complexity_allowlist.txt")),
        help="Path to allowlist file.",
    )
    parser.add_argument("--loc", type=int, default=DEFAULT_THRESHOLDS["line_count"])
    parser.add_argument("--functions", type=int, default=DEFAULT_THRESHOLDS["function_count"])
    parser.add_argument("--classes", type=int, default=DEFAULT_THRESHOLDS["class_count"])
    parser.add_argument(
        "--cc",
        type=int,
        default=DEFAULT_THRESHOLDS["cyclomatic_complexity"],
        help="Approximate branch count threshold (if/for/while/try).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = _get_repo_root()
    allowlist_path = repo_root / args.allowlist

    allowlist, allowlist_errors = _load_allowlist(allowlist_path)
    if allowlist_errors:
        print("Allowlist errors detected:")
        for err in allowlist_errors:
            print(f"- {err}")
        return 2

    if args.all:
        candidate_paths = [
            p for p in repo_root.rglob("*.py") if p.is_file()
        ]
    else:
        base_ref = _detect_base_ref(repo_root, args.base)
        changed = _collect_changed_files(repo_root, base_ref)
        normalized = [
            _normalize_path(repo_root, path_str) for path_str in sorted(changed)
        ]
        candidate_paths = [
            repo_root / path_str
            for path_str in normalized
            if path_str and path_str.endswith(".py")
        ]

    if not candidate_paths:
        print("No Python files to check.")
        return 0

    thresholds = {
        "line_count": args.loc,
        "function_count": args.functions,
        "class_count": args.classes,
        "cyclomatic_complexity": args.cc,
    }

    violations: List[str] = []
    for path in sorted(candidate_paths):
        rel_path = path.resolve().relative_to(repo_root).as_posix()
        metrics = analyze_file(path)
        if not metrics:
            continue

        if rel_path in allowlist:
            continue

        exceeded = {
            key: value
            for key, value in metrics.items()
            if value > thresholds.get(key, 0)
        }
        if exceeded:
            parts = [f"{key}={value}>{thresholds[key]}" for key, value in exceeded.items()]
            violations.append(f"{rel_path}: " + ", ".join(parts))

    if violations:
        print("Complexity check failed.")
        print(
            "Thresholds: "
            + ", ".join(
                f"{key}={value}"
                for key, value in thresholds.items()
            )
        )
        print("Violations:")
        for violation in violations:
            print(f"- {violation}")
        print(f"Allowlist: {allowlist_path}")
        return 1

    print("Complexity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
