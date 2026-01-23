"""
Guardrail test to prevent shell=True regression.

This test ensures that no production code uses subprocess with shell=True,
which is a security risk (command injection) and portability issue (Windows).

The hardening was done in PR #226 - this test prevents regression.
"""

import re
from pathlib import Path

import pytest

# Production code directories to scan
PRODUCTION_PATHS = [
    "swarm/tools",
    "packages/selftest-core/src",
]

# Allowlist for files that legitimately need shell=True (should be empty)
ALLOWLIST: list[str] = []

# Pattern to detect shell=True usage
SHELL_TRUE_PATTERN = re.compile(r"shell\s*=\s*True")


def find_python_files(base_path: Path) -> list[Path]:
    """Find all Python files under the given path."""
    return list(base_path.rglob("*.py"))


def scan_file_for_shell_true(file_path: Path) -> list[tuple[int, str]]:
    """
    Scan a file for shell=True occurrences.

    Returns list of (line_number, line_content) tuples.
    """
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), start=1):
            # Skip comments
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if SHELL_TRUE_PATTERN.search(line):
                violations.append((i, line.strip()))
    except Exception:
        pass  # Skip files that can't be read
    return violations


def test_no_shell_true_in_production_code():
    """
    Ensure no production code uses shell=True.

    shell=True is a security risk (command injection) and should be avoided.
    Use argv lists with shell=False instead:

    BAD:  subprocess.run("git status", shell=True, ...)
    GOOD: subprocess.run(["git", "status"], ...)

    If you truly need shell features, add the file to ALLOWLIST with justification.
    """
    repo_root = Path(__file__).parent.parent

    all_violations: list[tuple[Path, int, str]] = []

    for path_str in PRODUCTION_PATHS:
        base_path = repo_root / path_str
        if not base_path.exists():
            continue

        for py_file in find_python_files(base_path):
            # Check allowlist
            relative_path = str(py_file.relative_to(repo_root))
            if relative_path in ALLOWLIST:
                continue

            violations = scan_file_for_shell_true(py_file)
            for line_num, line_content in violations:
                all_violations.append((py_file, line_num, line_content))

    if all_violations:
        message_parts = [
            "Found shell=True in production code. This is a security risk.",
            "",
            "Violations:",
        ]
        for file_path, line_num, line_content in all_violations:
            relative = file_path.relative_to(repo_root)
            message_parts.append(f"  {relative}:{line_num}: {line_content}")

        message_parts.extend(
            [
                "",
                "Fix by converting to argv lists:",
                '  BAD:  subprocess.run("git status", shell=True, ...)',
                '  GOOD: subprocess.run(["git", "status"], ...)',
                "",
                "For string commands, use shlex.split():",
                "  import shlex",
                '  argv = shlex.split("git status")',
                "  subprocess.run(argv, ...)",
            ]
        )

        pytest.fail("\n".join(message_parts))


def test_allowlist_files_exist():
    """Ensure all files in ALLOWLIST actually exist."""
    repo_root = Path(__file__).parent.parent

    for path_str in ALLOWLIST:
        full_path = repo_root / path_str
        assert full_path.exists(), f"Allowlisted file does not exist: {path_str}"
