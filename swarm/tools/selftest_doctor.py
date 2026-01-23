#!/usr/bin/env python3
"""
Selftest Doctor

Diagnostic tool to determine whether selftest failures are due to:
- HARNESS_ISSUE: Python env, Rust toolchain, git state broken
- SERVICE_ISSUE: Code/config is actually broken
- HEALTHY: Everything is working normally
"""

import os
import subprocess
import sys
from typing import Any, Dict


class SelfTestDoctor:
    def diagnose(self) -> Dict[str, Any]:
        """
        Run diagnostic checks.

        Returns:
            {
                "harness": {
                    "python_env": "OK" | "ERROR" | "WARNING",
                    "rust_toolchain": "OK" | "ERROR" | "WARNING",
                    "git_state": "OK" | "ERROR" | "WARNING",
                },
                "service": {
                    "python_syntax": "OK" | "ERROR",
                    "cargo_check": "OK" | "ERROR",
                },
                "summary": "HEALTHY" | "HARNESS_ISSUE" | "SERVICE_ISSUE",
                "recommendations": ["..."],
            }
        """
        results = {"harness": {}, "service": {}, "recommendations": []}

        # Check Python environment
        try:
            if sys.version_info < (3, 8):
                results["harness"]["python_env"] = "ERROR"
                results["recommendations"].append("Upgrade to Python 3.8+")
            else:
                # Check if virtualenv active
                if not os.environ.get("VIRTUAL_ENV"):
                    results["harness"]["python_env"] = "WARNING"
                    results["recommendations"].append("Consider activating virtualenv: uv sync")
                else:
                    results["harness"]["python_env"] = "OK"
        except Exception as e:
            results["harness"]["python_env"] = "ERROR"
            results["recommendations"].append(f"Python error: {e}")

        # Check Rust toolchain
        try:
            result = subprocess.run(
                ["rustc", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                results["harness"]["rust_toolchain"] = "OK"
            else:
                results["harness"]["rust_toolchain"] = "ERROR"
                results["recommendations"].append("Install Rust: rustup install stable")
        except Exception:
            results["harness"]["rust_toolchain"] = "ERROR"
            results["recommendations"].append("Rust toolchain not found")

        # Check Git state
        try:
            # Check if in git repo
            result = subprocess.run(
                ["git", "status"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Check for dirty tree
                result = subprocess.run(
                    ["git", "diff", "--quiet"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    results["harness"]["git_state"] = "OK"
                else:
                    results["harness"]["git_state"] = "WARNING"
                    results["recommendations"].append("Git tree has uncommitted changes")
            else:
                results["harness"]["git_state"] = "ERROR"
                results["recommendations"].append("Not in git repository")
        except Exception:
            results["harness"]["git_state"] = "ERROR"
            results["recommendations"].append("Git check failed")

        # Check Python syntax
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", "swarm/tools/selftest.py"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                results["service"]["python_syntax"] = "ERROR"
                stderr = result.stderr.decode() if result.stderr else ""
                results["recommendations"].append(
                    f"Syntax error in selftest.py: {stderr[:100]}"
                )
            else:
                results["service"]["python_syntax"] = "OK"
        except Exception as e:
            results["service"]["python_syntax"] = "ERROR"
            results["recommendations"].append(f"Python syntax check failed: {e}")

        # Check cargo check (skip if no Cargo.toml)
        if not os.path.exists("Cargo.toml"):
            results["service"]["cargo_check"] = "OK"  # No Rust project, nothing to check
        else:
            try:
                result = subprocess.run(
                    ["cargo", "check"],
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    results["service"]["cargo_check"] = "OK"
                else:
                    results["service"]["cargo_check"] = "ERROR"
                    results["recommendations"].append("Cargo check failed: code has compile errors")
            except Exception as e:
                results["service"]["cargo_check"] = "ERROR"
                results["recommendations"].append(f"Cargo check failed: {e}")

        # Determine summary
        harness_values = results["harness"].values()
        service_values = results["service"].values()

        harness_ok = all(v in ("OK", "WARNING") for v in harness_values)
        service_ok = all(v in ("OK", "WARNING") for v in service_values)

        if not harness_ok:
            results["summary"] = "HARNESS_ISSUE"
        elif not service_ok:
            results["summary"] = "SERVICE_ISSUE"
        else:
            results["summary"] = "HEALTHY"

        return results


def main():
    import argparse
    import json as json_module

    parser = argparse.ArgumentParser(
        prog="selftest_doctor",
        description=(
            "Selftest Doctor - Diagnostic tool for selftest failures.\n\n"
            "Determines whether failures are due to:\n"
            "  - HARNESS_ISSUE: Python env, Rust toolchain, git state broken\n"
            "  - SERVICE_ISSUE: Code/config is actually broken\n"
            "  - HEALTHY: Everything is working normally"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed diagnostic output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    doctor = SelfTestDoctor()
    results = doctor.diagnose()

    # JSON output mode
    if args.json:
        print(json_module.dumps(results, indent=2))
        sys.exit(0 if results["summary"] == "HEALTHY" else 1)

    # Human-readable output
    print("=" * 70)
    print("SELFTEST DOCTOR DIAGNOSTICS")
    print("=" * 70)
    print()

    print("Harness Checks:")
    for check, status in results["harness"].items():
        icon = "OK" if status == "OK" else "WA" if status == "WARNING" else "ER"
        print(f"  [{icon}] {check:20s}: {status}")

    print("\nService Checks:")
    for check, status in results["service"].items():
        icon = "OK" if status == "OK" else "ER"
        print(f"  [{icon}] {check:20s}: {status}")

    print(f"\n{'=' * 70}")
    print(f"Summary: {results['summary']}")
    print(f"{'=' * 70}")

    if results["recommendations"]:
        print("\nRecommendations:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"  {i}. {rec}")
    else:
        print("\nNo issues detected")

    # Verbose mode: show additional context
    if args.verbose and results["recommendations"]:
        print("\n" + "-" * 70)
        print("Verbose: Run these commands to investigate further:")
        print("  - uv run pytest tests/ -v  # Run Python tests")
        print("  - cargo check              # Verify Rust compilation")
        print("  - git status               # Check working tree state")

    # Exit code based on summary
    if results["summary"] == "HEALTHY":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
