#!/usr/bin/env python3
"""
Tests for the Flow Studio smoke test fast path.

These tests verify that _run_smoke_test_inner() correctly interprets
selftest summary results and returns appropriate exit codes.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Add swarm/tools to path for imports
tools_path = Path(__file__).resolve().parents[1] / "swarm" / "tools"
sys.path.insert(0, str(tools_path))


@dataclass
class MockSelftestSnapshot:
    """Mock SelftestSnapshot for testing."""

    mode: str = "strict"
    status: str = "GREEN"
    kernel_ok: bool = True
    governance_ok: bool = True
    optional_ok: bool = True
    failed_steps: List[str] = field(default_factory=list)
    kernel_failed: List[str] = field(default_factory=list)
    governance_failed: List[str] = field(default_factory=list)
    optional_failed: List[str] = field(default_factory=list)


# Import modules to patch
import swarm.tools.status_provider as swarm_status_provider

import status_provider


def _apply_mock(monkeypatch, mock_fn):
    """Apply mock to both possible import paths."""
    monkeypatch.setattr(status_provider, "get_selftest_summary", mock_fn)
    monkeypatch.setattr(swarm_status_provider, "get_selftest_summary", mock_fn)

    # Clear module cache to force reimport
    for mod_name in list(sys.modules.keys()):
        if "flow_studio_smoke" in mod_name:
            del sys.modules[mod_name]


class TestFlowStudioSmokeHealthy:
    """Tests for healthy (all pass) scenarios."""

    def test_flowstudio_smoke_returns_0_when_healthy(self, monkeypatch):
        """When kernel_ok and governance_ok are True, return 0."""

        def mock_get_selftest_summary(*, degraded=False):
            return MockSelftestSnapshot(
                kernel_ok=True,
                governance_ok=True,
                failed_steps=[],
            )

        _apply_mock(monkeypatch, mock_get_selftest_summary)

        from flow_studio_smoke import _run_smoke_test_inner

        rc = _run_smoke_test_inner()
        assert rc == 0


class TestFlowStudioSmokeGovernanceFailure:
    """Tests for governance failure scenarios."""

    def test_flowstudio_smoke_returns_1_on_governance_failure(self, monkeypatch, capsys):
        """When governance_ok is False, return 1 and print BROKEN."""

        def mock_get_selftest_summary(*, degraded=False):
            return MockSelftestSnapshot(
                kernel_ok=True,
                governance_ok=False,
                status="YELLOW",
                failed_steps=["agents-governance"],
                governance_failed=["agents-governance"],
            )

        _apply_mock(monkeypatch, mock_get_selftest_summary)

        from flow_studio_smoke import _run_smoke_test_inner

        rc = _run_smoke_test_inner()
        captured = capsys.readouterr()

        assert rc == 1
        assert "BROKEN" in captured.out
        assert "agents-governance" in captured.out


class TestFlowStudioSmokeKernelFailure:
    """Tests for kernel failure scenarios."""

    def test_flowstudio_smoke_returns_1_on_kernel_failure(self, monkeypatch, capsys):
        """When kernel_ok is False, return 1 and print BROKEN."""

        def mock_get_selftest_summary(*, degraded=False):
            return MockSelftestSnapshot(
                kernel_ok=False,
                governance_ok=False,
                status="RED",
                failed_steps=["core-checks"],
                kernel_failed=["core-checks"],
            )

        _apply_mock(monkeypatch, mock_get_selftest_summary)

        from flow_studio_smoke import _run_smoke_test_inner

        rc = _run_smoke_test_inner()
        captured = capsys.readouterr()

        assert rc == 1
        assert "BROKEN" in captured.out
        assert "core-checks" in captured.out


class TestFlowStudioSmokeFatalError:
    """Tests for fatal error scenarios."""

    def test_flowstudio_smoke_returns_2_on_exception(self, monkeypatch, capsys):
        """When get_selftest_summary raises, return 2 and print FATAL."""

        def mock_get_selftest_summary(*, degraded=False):
            raise RuntimeError("Test explosion")

        _apply_mock(monkeypatch, mock_get_selftest_summary)

        from flow_studio_smoke import _run_smoke_test_inner

        rc = _run_smoke_test_inner()
        captured = capsys.readouterr()

        assert rc == 2
        assert "FATAL" in captured.out or "FATAL" in captured.err


class TestFlowStudioSmokeOutput:
    """Tests for output formatting."""

    def test_healthy_output_includes_kernel_ok(self, monkeypatch, capsys):
        """Output should show KERNEL: OK when healthy."""

        def mock_get_selftest_summary(*, degraded=False):
            return MockSelftestSnapshot(
                kernel_ok=True,
                governance_ok=True,
            )

        _apply_mock(monkeypatch, mock_get_selftest_summary)

        from flow_studio_smoke import _run_smoke_test_inner

        _run_smoke_test_inner()
        captured = capsys.readouterr()

        assert "KERNEL:" in captured.out
        assert "OK" in captured.out

    def test_failure_output_includes_actionable_hints(self, monkeypatch, capsys):
        """Output should include actionable hints on failure."""

        def mock_get_selftest_summary(*, degraded=False):
            return MockSelftestSnapshot(
                kernel_ok=True,
                governance_ok=False,
                status="YELLOW",
                failed_steps=["agents-governance"],
                governance_failed=["agents-governance"],
            )

        _apply_mock(monkeypatch, mock_get_selftest_summary)

        from flow_studio_smoke import _run_smoke_test_inner

        _run_smoke_test_inner()
        captured = capsys.readouterr()

        # Should include rerun hint
        assert "selftest.py --step" in captured.out or "selftest.py --degraded" in captured.out
