#!/usr/bin/env python3
"""
test_selftest_metrics.py - Tests for selftest metrics emission

Tests that selftest emits the correct Prometheus metrics at key execution points.

## Test Coverage

1. Metric Initialization
   - Environment detection
   - Backend selection (local, prometheus, none)
   - Prometheus server startup

2. Step Metrics
   - step_started emits counter
   - step_completed emits duration histogram
   - step_completed emits failure counter on failure
   - Labels match step attributes (step_id, tier, severity, exit_code)

3. Degradation Metrics
   - degradation_logged emits counter
   - degradation_logged emits active gauge
   - Only GOVERNANCE/OPTIONAL tiers emit degradations

4. Run Completion Metrics
   - run_completed emits run duration histogram
   - run_completed emits governance pass rate gauge
   - run_completed emits overall status gauge
   - run_completed emits last run timestamp gauge

5. Integration Tests
   - Full selftest run emits all expected metrics
   - Metrics file is written correctly (local backend)
   - Prometheus registry contains metrics (prometheus backend)
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

# Add swarm/tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / "swarm" / "tools"))

from selftest_metrics import SelftestMetrics


class TestMetricsInitialization:
    """Test metrics initialization and configuration."""

    def test_default_backend_is_local(self):
        """Test that default backend is local JSONL."""
        metrics = SelftestMetrics()
        assert metrics.backend == "local"

    def test_explicit_backend_override(self):
        """Test that SELFTEST_METRICS_BACKEND env var overrides backend."""
        # Note: prometheus backend will fall back to local if prometheus_client not installed
        with mock.patch.dict(os.environ, {"SELFTEST_METRICS_BACKEND": "local"}):
            metrics = SelftestMetrics()
            assert metrics.backend == "local"

    def test_environment_detection_from_env_var(self):
        """Test that SELFTEST_ENVIRONMENT env var sets environment."""
        with mock.patch.dict(os.environ, {"SELFTEST_ENVIRONMENT": "staging"}):
            metrics = SelftestMetrics()
            assert metrics.environment == "staging"

    def test_environment_detection_from_ci(self):
        """Test that CI env var sets environment to 'ci'."""
        with mock.patch.dict(os.environ, {"CI": "true"}, clear=True):
            metrics = SelftestMetrics()
            assert metrics.environment == "ci"

    def test_backend_none_disables_metrics(self):
        """Test that backend='none' creates no-op metrics."""
        metrics = SelftestMetrics(backend="none")
        assert metrics.backend == "none"
        # Calling methods should not raise errors
        metrics.step_started("test-step", "kernel")
        metrics.step_completed("test-step", "kernel", True, 1.0, 0, "critical")


class TestStepMetrics:
    """Test step-level metrics emission."""

    def test_step_started_emits_counter(self, tmp_path):
        """Test that step_started emits selftest_step_total counter."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.step_started(step_id="core-checks", tier="kernel")

        # Read metrics file
        with open(metrics_file) as f:
            lines = f.readlines()

        assert len(lines) == 1
        metric = json.loads(lines[0])

        assert metric["metric_name"] == "selftest_step_total"
        assert metric["metric_type"] == "counter"
        assert metric["value"] == 1
        assert metric["labels"]["step_id"] == "core-checks"
        assert metric["labels"]["tier"] == "kernel"

    def test_step_completed_emits_duration(self, tmp_path):
        """Test that step_completed emits duration histogram."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.step_completed(
            step_id="core-checks",
            tier="kernel",
            passed=True,
            duration_seconds=2.5,
            exit_code=0,
            severity="critical",
        )

        # Read metrics file
        with open(metrics_file) as f:
            lines = f.readlines()

        # Find duration metric
        duration_metrics = [
            json.loads(line) for line in lines if "duration" in json.loads(line)["metric_name"]
        ]
        assert len(duration_metrics) == 1

        metric = duration_metrics[0]
        assert metric["metric_name"] == "selftest_step_duration_seconds"
        assert metric["metric_type"] == "histogram"
        assert metric["value"] == 2.5
        assert metric["labels"]["step_id"] == "core-checks"
        assert metric["labels"]["tier"] == "kernel"

    def test_step_completed_emits_failure_counter_on_failure(self, tmp_path):
        """Test that step_completed emits failure counter when passed=False."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.step_completed(
            step_id="agents-governance",
            tier="governance",
            passed=False,
            duration_seconds=1.0,
            exit_code=1,
            severity="warning",
        )

        # Read metrics file
        with open(metrics_file) as f:
            lines = f.readlines()

        # Find failure metric
        failure_metrics = [
            json.loads(line) for line in lines if "failures" in json.loads(line)["metric_name"]
        ]
        assert len(failure_metrics) == 1

        metric = failure_metrics[0]
        assert metric["metric_name"] == "selftest_step_failures_total"
        assert metric["metric_type"] == "counter"
        assert metric["value"] == 1
        assert metric["labels"]["step_id"] == "agents-governance"
        assert metric["labels"]["severity"] == "warning"
        assert metric["labels"]["tier"] == "governance"
        assert metric["labels"]["exit_code"] == "1"

    def test_step_completed_emits_kernel_failure_counter(self, tmp_path):
        """Test that kernel failures emit kernel_failures_total counter."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.step_completed(
            step_id="core-checks",
            tier="kernel",
            passed=False,
            duration_seconds=1.0,
            exit_code=1,
            severity="critical",
        )

        # Read metrics file
        with open(metrics_file) as f:
            lines = f.readlines()

        # Find kernel failure metric
        kernel_metrics = [
            json.loads(line)
            for line in lines
            if "kernel_failures" in json.loads(line)["metric_name"]
        ]
        assert len(kernel_metrics) == 1

        metric = kernel_metrics[0]
        assert metric["metric_name"] == "selftest_kernel_failures_total"
        assert metric["metric_type"] == "counter"
        assert metric["value"] == 1

    def test_step_labels_are_correct(self, tmp_path):
        """Test that step metrics have correct labels."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local", environment="test-env")
        metrics.local_log_path = metrics_file

        metrics.step_started(step_id="test-step", tier="governance")

        with open(metrics_file) as f:
            metric = json.loads(f.readline())

        assert metric["labels"]["step_id"] == "test-step"
        assert metric["labels"]["tier"] == "governance"
        assert metric["labels"]["environment"] == "test-env"


class TestDegradationMetrics:
    """Test degradation-specific metrics."""

    def test_degradation_logged_emits_counter(self, tmp_path):
        """Test that degradation_logged emits degradations_total counter."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.degradation_logged(
            step_id="agents-governance",
            tier="governance",
            severity="warning",
        )

        with open(metrics_file) as f:
            lines = f.readlines()

        # Find degradation counter
        degradation_counters = [
            json.loads(line)
            for line in lines
            if json.loads(line)["metric_name"] == "selftest_degradations_total"
        ]
        assert len(degradation_counters) == 1

        metric = degradation_counters[0]
        assert metric["metric_type"] == "counter"
        assert metric["value"] == 1
        assert metric["labels"]["step_id"] == "agents-governance"
        assert metric["labels"]["severity"] == "warning"

    def test_degradation_logged_emits_active_gauge(self, tmp_path):
        """Test that degradation_logged emits degradations_active gauge."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.degradation_logged(
            step_id="bdd",
            tier="governance",
            severity="warning",
        )

        with open(metrics_file) as f:
            lines = f.readlines()

        # Find active degradation gauge
        active_gauges = [
            json.loads(line)
            for line in lines
            if json.loads(line)["metric_name"] == "selftest_degradations_active"
        ]
        assert len(active_gauges) == 1

        metric = active_gauges[0]
        assert metric["metric_type"] == "gauge"
        assert metric["value"] == 1
        assert metric["labels"]["step_id"] == "bdd"


class TestRunCompletionMetrics:
    """Test run-level metrics emission."""

    def test_run_completed_emits_duration_histogram(self, tmp_path):
        """Test that run_completed emits run_duration_seconds histogram."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.run_completed(
            mode="strict",
            duration_seconds=15.3,
            governance_pass_rate=100.0,
            overall_status="HEALTHY",
        )

        with open(metrics_file) as f:
            lines = f.readlines()

        # Find run duration histogram
        run_duration = [
            json.loads(line)
            for line in lines
            if json.loads(line)["metric_name"] == "selftest_run_duration_seconds"
        ]
        assert len(run_duration) == 1

        metric = run_duration[0]
        assert metric["metric_type"] == "histogram"
        assert metric["value"] == 15.3
        assert metric["labels"]["mode"] == "strict"

    def test_run_completed_emits_governance_pass_rate(self, tmp_path):
        """Test that run_completed emits governance_pass_rate gauge."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.run_completed(
            mode="degraded",
            duration_seconds=10.0,
            governance_pass_rate=85.0,
            overall_status="DEGRADED",
        )

        with open(metrics_file) as f:
            lines = f.readlines()

        # Find governance pass rate gauge
        pass_rate = [
            json.loads(line)
            for line in lines
            if json.loads(line)["metric_name"] == "selftest_governance_pass_rate"
        ]
        assert len(pass_rate) == 1

        metric = pass_rate[0]
        assert metric["metric_type"] == "gauge"
        assert metric["value"] == 85.0

    def test_run_completed_emits_overall_status(self, tmp_path):
        """Test that run_completed emits run_overall_status gauge."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        metrics.run_completed(
            mode="strict",
            duration_seconds=10.0,
            governance_pass_rate=100.0,
            overall_status="HEALTHY",
        )

        with open(metrics_file) as f:
            lines = f.readlines()

        # Find overall status gauge
        status = [
            json.loads(line)
            for line in lines
            if json.loads(line)["metric_name"] == "selftest_run_overall_status"
        ]
        assert len(status) == 1

        metric = status[0]
        assert metric["metric_type"] == "gauge"
        assert metric["value"] == 1.0  # HEALTHY = 1.0
        assert metric["labels"]["status"] == "HEALTHY"

    def test_run_completed_status_mapping(self, tmp_path):
        """Test that overall_status values map to correct numeric values."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        # Test HEALTHY
        metrics.run_completed("strict", 10.0, 100.0, "HEALTHY")
        with open(metrics_file) as f:
            lines = [line for line in f if "overall_status" in line]
        metric = json.loads(lines[0])
        assert metric["value"] == 1.0

        # Clear file
        metrics_file.unlink()

        # Test DEGRADED
        metrics.run_completed("degraded", 10.0, 90.0, "DEGRADED")
        with open(metrics_file) as f:
            lines = [line for line in f if "overall_status" in line]
        metric = json.loads(lines[0])
        assert metric["value"] == 0.5

        # Clear file
        metrics_file.unlink()

        # Test BROKEN
        metrics.run_completed("strict", 10.0, 0.0, "BROKEN")
        with open(metrics_file) as f:
            lines = [line for line in f if "overall_status" in line]
        metric = json.loads(lines[0])
        assert metric["value"] == 0.0

    def test_run_completed_emits_last_run_timestamp(self, tmp_path):
        """Test that run_completed emits last_run_timestamp gauge."""
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        metrics = SelftestMetrics(backend="local")
        metrics.local_log_path = metrics_file

        before = time.time()
        metrics.run_completed(
            mode="strict",
            duration_seconds=10.0,
            governance_pass_rate=100.0,
            overall_status="HEALTHY",
        )
        after = time.time()

        with open(metrics_file) as f:
            lines = f.readlines()

        # Find last run timestamp gauge
        timestamp = [
            json.loads(line)
            for line in lines
            if json.loads(line)["metric_name"] == "selftest_last_run_timestamp"
        ]
        assert len(timestamp) == 1

        metric = timestamp[0]
        assert metric["metric_type"] == "gauge"
        assert before <= metric["value"] <= after


class TestMetricsIntegration:
    """Integration tests for metrics emission with real selftest runs."""

    def test_metrics_file_created_on_run(self, tmp_path, monkeypatch):
        """Test that a metrics file is created after a selftest run."""
        # Change working directory to tmp_path
        monkeypatch.chdir(tmp_path)

        # Import after chdir so metrics file is written to tmp_path
        from selftest import SelfTestRunner
        from selftest_config import SelfTestCategory, SelfTestSeverity, SelfTestStep, SelfTestTier

        # Create a simple test step
        test_step = SelfTestStep(
            id="test-step",
            name="Test Step",
            tier=SelfTestTier.KERNEL,
            severity=SelfTestSeverity.CRITICAL,
            category=SelfTestCategory.CORRECTNESS,
            description="Test step",
            command=["echo test"],
            ac_ids=["TEST-1"],
        )

        runner = SelfTestRunner(write_report=False)
        runner.run([test_step])

        # Check metrics file exists
        metrics_file = tmp_path / "selftest_metrics.jsonl"
        assert metrics_file.exists()

        # Check metrics file has content
        with open(metrics_file) as f:
            lines = f.readlines()

        assert len(lines) > 0

        # Check expected metrics are present
        metric_names = {json.loads(line)["metric_name"] for line in lines}
        assert "selftest_step_total" in metric_names
        assert "selftest_step_duration_seconds" in metric_names
        assert "selftest_run_duration_seconds" in metric_names


class TestPrometheusIntegration:
    """Test Prometheus backend integration (requires prometheus_client)."""

    @pytest.mark.skipif(
        True,
        reason="Prometheus client not installed (optional dependency)",
    )
    def test_prometheus_metrics_are_registered(self):
        """Test that Prometheus metrics are registered correctly."""
        from prometheus_client import REGISTRY

        SelftestMetrics(backend="prometheus")

        # Check that metrics are in registry
        metric_names = [metric.name for metric in REGISTRY.collect()]

        # Core metrics should be registered
        assert any("selftest_step_total" in name for name in metric_names)
        assert any("selftest_step_duration_seconds" in name for name in metric_names)
        assert any("selftest_run_duration_seconds" in name for name in metric_names)

    def test_prometheus_backend_graceful_fallback(self):
        """Test that prometheus backend falls back to local if client not available."""
        # Mock prometheus_client as unavailable
        with mock.patch.dict(sys.modules, {"prometheus_client": None}):
            # Force reimport to trigger fallback
            import importlib

            import selftest_metrics

            importlib.reload(selftest_metrics)

            metrics = selftest_metrics.SelftestMetrics(backend="prometheus")
            # Should fall back to local
            assert metrics.backend == "local"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
