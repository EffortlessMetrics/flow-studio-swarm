#!/usr/bin/env python3
"""
selftest_metrics.py - Metrics emission for selftest system

This module provides Prometheus-compatible metrics for monitoring selftest health.
It follows the observability spec defined in docs/SELFTEST_OBSERVABILITY_SPEC.md.

## Metrics Emitted

### Counters
- selftest_step_total: Total number of step executions (labels: step_id, environment, tier)
- selftest_step_failures_total: Total failures (labels: step_id, severity, environment, tier, exit_code)
- selftest_degradations_total: Total degradations logged (labels: step_id, severity, environment, tier)
- selftest_kernel_failures_total: Total KERNEL-tier failures (labels: environment)

### Histograms
- selftest_step_duration_seconds: Step execution time (labels: step_id, environment, tier)
- selftest_run_duration_seconds: Total run time (labels: mode, environment)

### Gauges
- selftest_governance_pass_rate: % of governance steps passing (labels: environment)
- selftest_degradations_active: Current active degradations (labels: step_id, severity, environment, tier)
- selftest_run_overall_status: Overall health status (labels: status, environment)
- selftest_last_run_timestamp: Unix timestamp of last run (labels: environment)

## Usage

```python
from selftest_metrics import SelftestMetrics

# Initialize metrics
metrics = SelftestMetrics(environment="dev")

# Emit step start
metrics.step_started(step_id="core-checks", tier="kernel")

# Emit step completion
metrics.step_completed(
    step_id="core-checks",
    tier="kernel",
    passed=True,
    duration_seconds=2.5,
    exit_code=0,
    severity="critical"
)

# Emit degradation
metrics.degradation_logged(
    step_id="agents-governance",
    tier="governance",
    severity="warning"
)

# Emit run summary
metrics.run_completed(
    mode="strict",
    duration_seconds=15.3,
    governance_pass_rate=100.0,
    overall_status="HEALTHY"
)
```

## Environment Detection

The metrics backend is chosen based on environment variables:

1. SELFTEST_METRICS_BACKEND (explicit override): "prometheus", "local", "none"
2. Auto-detection:
   - PROMETHEUS_MULTIPROC_DIR → prometheus
   - Default → local (JSONL)
3. "none" → no-op (metrics disabled)

## Prometheus Integration

To enable Prometheus metrics:
```bash
export SELFTEST_METRICS_BACKEND=prometheus
export SELFTEST_METRICS_PORT=9091  # optional, default 9091
```

Metrics will be exposed at http://localhost:9091/metrics
"""

import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Prometheus client is optional (graceful fallback if not available)
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Define no-op classes for when prometheus_client is not available
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def set(self, *args, **kwargs):
            pass


# Histogram buckets for step duration (from observability spec)
STEP_DURATION_BUCKETS = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]

# Histogram buckets for run duration (from observability spec)
RUN_DURATION_BUCKETS = [5.0, 10.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0]


class SelftestMetrics:
    """
    Metrics collector for selftest system.

    Emits metrics to Prometheus or local JSONL based on environment detection.
    """

    def __init__(self, environment: Optional[str] = None, backend: Optional[str] = None):
        """
        Initialize metrics collector.

        Args:
            environment: Execution environment (dev, staging, prod). Defaults to hostname.
            backend: Metrics backend ("prometheus", "local", "none"). Defaults to auto-detect.
        """
        self.environment = environment or self._detect_environment()
        self.backend = backend or self._detect_backend()
        self.metrics_started = False

        # Local JSONL log path
        self.local_log_path = Path("selftest_metrics.jsonl")

        # Initialize Prometheus metrics if backend is prometheus
        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self._init_prometheus_metrics()
            self._start_prometheus_server()
        elif self.backend == "prometheus" and not PROMETHEUS_AVAILABLE:
            # Silently fall back to local backend if prometheus_client not available
            # (warning would interfere with JSON output in selftest)
            self.backend = "local"

    def _detect_environment(self) -> str:
        """Detect execution environment from env vars or hostname."""
        env = os.getenv("SELFTEST_ENVIRONMENT")
        if env:
            return env

        # Check CI environment
        if os.getenv("CI"):
            return "ci"
        if os.getenv("GITHUB_ACTIONS"):
            return "ci"

        # Default to hostname
        return socket.gethostname()

    def _detect_backend(self) -> str:
        """
        Detect which metrics backend to use.

        Priority:
        1. SELFTEST_METRICS_BACKEND (explicit override)
        2. Auto-detection (PROMETHEUS_MULTIPROC_DIR → prometheus)
        3. Default: local JSONL
        """
        backend = os.getenv("SELFTEST_METRICS_BACKEND")
        if backend:
            return backend.lower()

        # Check for Prometheus multiprocess mode
        if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
            return "prometheus"

        # Default to local
        return "local"

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metric objects."""
        # Counters
        self.prom_step_total = Counter(
            "selftest_step_total",
            "Total number of selftest step executions",
            ["step_id", "environment", "tier"],
        )

        self.prom_step_failures_total = Counter(
            "selftest_step_failures_total",
            "Total number of selftest step failures",
            ["step_id", "severity", "environment", "tier", "exit_code"],
        )

        self.prom_degradations_total = Counter(
            "selftest_degradations_total",
            "Total number of degradations logged",
            ["step_id", "severity", "environment", "tier"],
        )

        self.prom_kernel_failures_total = Counter(
            "selftest_kernel_failures_total",
            "Total number of KERNEL-tier step failures",
            ["environment"],
        )

        # Histograms
        self.prom_step_duration = Histogram(
            "selftest_step_duration_seconds",
            "Execution time for each selftest step",
            ["step_id", "environment", "tier"],
            buckets=STEP_DURATION_BUCKETS,
        )

        self.prom_run_duration = Histogram(
            "selftest_run_duration_seconds",
            "Total execution time for an entire selftest run",
            ["mode", "environment"],
            buckets=RUN_DURATION_BUCKETS,
        )

        # Gauges
        self.prom_governance_pass_rate = Gauge(
            "selftest_governance_pass_rate",
            "Percentage of governance steps passing (0-100)",
            ["environment"],
        )

        self.prom_degradations_active = Gauge(
            "selftest_degradations_active",
            "Number of currently active degradations",
            ["step_id", "severity", "environment", "tier"],
        )

        self.prom_run_overall_status = Gauge(
            "selftest_run_overall_status",
            "Current overall selftest health status (0=BROKEN, 0.5=DEGRADED, 1=HEALTHY)",
            ["status", "environment"],
        )

        self.prom_last_run_timestamp = Gauge(
            "selftest_last_run_timestamp",
            "Unix timestamp of last selftest run",
            ["environment"],
        )

    def _start_prometheus_server(self):
        """Start Prometheus HTTP server if not already running."""
        if self.metrics_started:
            return

        try:
            port = int(os.getenv("SELFTEST_METRICS_PORT", "9091"))
            start_http_server(port)
            self.metrics_started = True
        except OSError as e:
            # Server might already be running (e.g., in tests)
            if "Address already in use" in str(e):
                self.metrics_started = True
            else:
                raise

    def _emit_local(self, metric_name: str, metric_type: str, value: float, labels: dict):
        """Write metric to local JSONL file."""
        if self.backend != "local":
            return

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric_name": metric_name,
            "metric_type": metric_type,
            "value": value,
            "labels": labels,
        }

        try:
            with open(self.local_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Warning: Failed to write metric to {self.local_log_path}: {e}", file=sys.stderr)

    def step_started(self, step_id: str, tier: str):
        """
        Emit metric when a step starts execution.

        Args:
            step_id: Step identifier (e.g., "core-checks")
            tier: Step tier ("kernel", "governance", "optional")
        """
        labels = {
            "step_id": step_id,
            "environment": self.environment,
            "tier": tier,
        }

        # Prometheus
        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self.prom_step_total.labels(**labels).inc()

        # Local
        self._emit_local("selftest_step_total", "counter", 1, labels)

    def step_completed(
        self,
        step_id: str,
        tier: str,
        passed: bool,
        duration_seconds: float,
        exit_code: int,
        severity: str,
    ):
        """
        Emit metrics when a step completes execution.

        Args:
            step_id: Step identifier
            tier: Step tier ("kernel", "governance", "optional")
            passed: Whether step passed
            duration_seconds: Execution time in seconds
            exit_code: Command exit code
            severity: Step severity ("critical", "warning", "info")
        """
        # Duration histogram
        duration_labels = {
            "step_id": step_id,
            "environment": self.environment,
            "tier": tier,
        }

        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self.prom_step_duration.labels(**duration_labels).observe(duration_seconds)

        self._emit_local(
            "selftest_step_duration_seconds", "histogram", duration_seconds, duration_labels
        )

        # Failure counter
        if not passed:
            failure_labels = {
                "step_id": step_id,
                "severity": severity,
                "environment": self.environment,
                "tier": tier,
                "exit_code": str(exit_code),
            }

            if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
                self.prom_step_failures_total.labels(**failure_labels).inc()

            self._emit_local("selftest_step_failures_total", "counter", 1, failure_labels)

            # Kernel failure counter
            if tier == "kernel":
                kernel_labels = {"environment": self.environment}

                if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
                    self.prom_kernel_failures_total.labels(**kernel_labels).inc()

                self._emit_local("selftest_kernel_failures_total", "counter", 1, kernel_labels)

    def degradation_logged(self, step_id: str, tier: str, severity: str):
        """
        Emit metric when a degradation is logged.

        Args:
            step_id: Step identifier
            tier: Step tier ("governance" or "optional")
            severity: Degradation severity ("critical", "warning", "info")
        """
        labels = {
            "step_id": step_id,
            "severity": severity,
            "environment": self.environment,
            "tier": tier,
        }

        # Counter
        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self.prom_degradations_total.labels(**labels).inc()

        self._emit_local("selftest_degradations_total", "counter", 1, labels)

        # Gauge (active degradations)
        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self.prom_degradations_active.labels(**labels).inc()

        self._emit_local("selftest_degradations_active", "gauge", 1, labels)

    def run_completed(
        self,
        mode: str,
        duration_seconds: float,
        governance_pass_rate: float,
        overall_status: str,
    ):
        """
        Emit summary metrics when a run completes.

        Args:
            mode: Selftest mode ("strict", "degraded", "kernel-only")
            duration_seconds: Total run time in seconds
            governance_pass_rate: Percentage of governance steps passing (0-100)
            overall_status: Overall status ("HEALTHY", "DEGRADED", "BROKEN")
        """
        # Run duration histogram
        duration_labels = {
            "mode": mode,
            "environment": self.environment,
        }

        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self.prom_run_duration.labels(**duration_labels).observe(duration_seconds)

        self._emit_local(
            "selftest_run_duration_seconds", "histogram", duration_seconds, duration_labels
        )

        # Governance pass rate gauge
        governance_labels = {"environment": self.environment}

        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self.prom_governance_pass_rate.labels(**governance_labels).set(governance_pass_rate)

        self._emit_local(
            "selftest_governance_pass_rate", "gauge", governance_pass_rate, governance_labels
        )

        # Overall status gauge
        status_map = {"HEALTHY": 1.0, "DEGRADED": 0.5, "BROKEN": 0.0}
        status_value = status_map.get(overall_status, 0.0)
        status_labels = {
            "status": overall_status,
            "environment": self.environment,
        }

        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self.prom_run_overall_status.labels(**status_labels).set(status_value)

        self._emit_local("selftest_run_overall_status", "gauge", status_value, status_labels)

        # Last run timestamp
        timestamp_labels = {"environment": self.environment}
        current_timestamp = datetime.now(timezone.utc).timestamp()

        if self.backend == "prometheus" and PROMETHEUS_AVAILABLE:
            self.prom_last_run_timestamp.labels(**timestamp_labels).set(current_timestamp)

        self._emit_local(
            "selftest_last_run_timestamp", "gauge", current_timestamp, timestamp_labels
        )
