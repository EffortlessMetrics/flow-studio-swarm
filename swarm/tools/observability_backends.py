#!/usr/bin/env python3
"""
Observability backends for selftest metrics and events.

Provides pluggable backends for emitting selftest metrics to various
monitoring systems:
- Prometheus (in-memory metrics, HTTP endpoint, or pushgateway)
- Datadog (cloud-based monitoring)
- CloudWatch (AWS monitoring)
- Logs (structured JSON or text output)

Design principles:
- Graceful degradation: Missing credentials don't crash selftest
- Backend abstraction: Easy to add new backends
- Zero-config default: Logs always work, others opt-in
- Multi-backend: All enabled backends receive events
"""

import json
import logging
import os
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.utils.yaml_utils import load_yaml

# Configure logging for this module
logger = logging.getLogger(__name__)


class ObservabilityBackend(ABC):
    """
    Abstract base class for observability backends.

    All backends must implement these methods to receive selftest events.
    """

    @abstractmethod
    def emit_run_started(self, run_id: str, tier: str, timestamp: float) -> None:
        """
        Emit event when a selftest run starts.

        Args:
            run_id: Unique identifier for this run
            tier: Test tier ('kernel', 'governance', 'optional', or 'all')
            timestamp: Unix timestamp when run started
        """
        pass

    @abstractmethod
    def emit_step_completed(self, step_id: str, duration_ms: int, result: str, tier: str) -> None:
        """
        Emit event when a selftest step completes.

        Args:
            step_id: Step identifier (e.g., 'core-checks')
            duration_ms: Step duration in milliseconds
            result: Step result ('PASS', 'FAIL', 'SKIP')
            tier: Step tier ('kernel', 'governance', 'optional')
        """
        pass

    @abstractmethod
    def emit_step_failed(self, step_id: str, severity: str, error_message: str, tier: str) -> None:
        """
        Emit event when a selftest step fails.

        Args:
            step_id: Step identifier
            severity: Failure severity ('critical', 'warning', 'info')
            error_message: Error message or output
            tier: Step tier
        """
        pass

    @abstractmethod
    def emit_run_completed(self, run_id: str, result: str, duration_ms: int, summary: Dict[str, Any]) -> None:
        """
        Emit event when a selftest run completes.

        Args:
            run_id: Unique identifier for this run
            result: Overall result ('PASS', 'FAIL')
            duration_ms: Total run duration in milliseconds
            summary: Summary dict with passed/failed/skipped counts
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close backend resources (flush buffers, close connections, etc.).
        Called at end of selftest run.
        """
        pass


class PrometheusBackend(ObservabilityBackend):
    """
    Prometheus backend for selftest metrics.

    Uses prometheus_client to expose metrics via HTTP endpoint or push to gateway.
    """

    def __init__(self, config: Dict[str, Any], strict_mode: bool = False):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.pushgateway_url = config.get("pushgateway_url")
        self.serve_port = config.get("serve_port", 8000)
        self.serve_addr = config.get("serve_addr", "127.0.0.1")
        self.job_name = config.get("job_name", "selftest")
        self.labels = config.get("labels", {})
        self.strict_mode = strict_mode

        # Try to import prometheus_client
        try:
            from prometheus_client import (
                CollectorRegistry,
                Counter,
                Histogram,
                push_to_gateway,
                start_http_server,
            )

            self.prom = True
            self.registry = CollectorRegistry()

            # Define metrics
            self.runs_total = Counter(
                "selftest_runs_total",
                "Total number of selftest runs",
                ["tier", "result"],
                registry=self.registry,
            )

            self.steps_total = Counter(
                "selftest_steps_total",
                "Total number of selftest steps",
                ["step_id", "tier", "result"],
                registry=self.registry,
            )

            self.step_duration = Histogram(
                "selftest_step_duration_seconds",
                "Duration of selftest steps in seconds",
                ["step_id", "tier"],
                registry=self.registry,
            )

            self.run_duration = Histogram(
                "selftest_run_duration_seconds",
                "Duration of selftest runs in seconds",
                ["tier"],
                registry=self.registry,
            )

            self.failures_total = Counter(
                "selftest_failures_total",
                "Total number of selftest failures",
                ["step_id", "tier", "severity"],
                registry=self.registry,
            )

            # Start HTTP server if not using pushgateway
            if not self.pushgateway_url:
                try:
                    # Support ephemeral ports: if serve_port is 0, OS picks an available port
                    # This prevents "Address already in use" errors in test/smoke environments
                    if self.serve_port == 0:
                        # Ephemeral port mode - let OS choose
                        import socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.bind((self.serve_addr, 0))
                        actual_port = sock.getsockname()[1]
                        sock.close()
                        start_http_server(actual_port, self.serve_addr, registry=self.registry)
                        logger.info(f"Prometheus metrics server started on {self.serve_addr}:{actual_port} (ephemeral)")
                    else:
                        start_http_server(self.serve_port, self.serve_addr, registry=self.registry)
                        logger.info(f"Prometheus metrics server started on {self.serve_addr}:{self.serve_port}")
                except OSError as e:
                    if "Address already in use" in str(e):
                        logger.warning(f"Prometheus port {self.serve_port} already in use; skipping metrics server (likely already running)")
                    elif self.strict_mode:
                        raise RuntimeError(f"Failed to start Prometheus HTTP server: {e}") from e
                    else:
                        logger.warning(f"Failed to start Prometheus HTTP server: {e}")
                except Exception as e:
                    if self.strict_mode:
                        raise RuntimeError(f"Failed to start Prometheus HTTP server: {e}") from e
                    logger.warning(f"Failed to start Prometheus HTTP server: {e}")

            self.push_to_gateway = push_to_gateway

        except ImportError:
            logger.warning("prometheus_client not installed, Prometheus backend disabled")
            self.prom = False
            self.enabled = False

    def emit_run_started(self, run_id: str, tier: str, timestamp: float) -> None:
        if not self.enabled or not self.prom:
            return
        # No-op for Prometheus (we track completion, not start)

    def emit_step_completed(self, step_id: str, duration_ms: int, result: str, tier: str) -> None:
        if not self.enabled or not self.prom:
            return
        try:
            self.steps_total.labels(step_id=step_id, tier=tier, result=result).inc()
            self.step_duration.labels(step_id=step_id, tier=tier).observe(duration_ms / 1000.0)
        except Exception as e:
            logger.warning(f"Failed to emit step_completed to Prometheus: {e}")

    def emit_step_failed(self, step_id: str, severity: str, error_message: str, tier: str) -> None:
        if not self.enabled or not self.prom:
            return
        try:
            self.failures_total.labels(step_id=step_id, tier=tier, severity=severity).inc()
        except Exception as e:
            logger.warning(f"Failed to emit step_failed to Prometheus: {e}")

    def emit_run_completed(self, run_id: str, result: str, duration_ms: int, summary: Dict[str, Any]) -> None:
        if not self.enabled or not self.prom:
            return
        try:
            tier = summary.get("mode", "strict")
            self.runs_total.labels(tier=tier, result=result).inc()
            self.run_duration.labels(tier=tier).observe(duration_ms / 1000.0)

            # Push to gateway if configured
            if self.pushgateway_url:
                self.push_to_gateway(self.pushgateway_url, job=self.job_name, registry=self.registry)
                logger.info(f"Pushed metrics to Prometheus pushgateway at {self.pushgateway_url}")

        except Exception as e:
            logger.warning(f"Failed to emit run_completed to Prometheus: {e}")

    def close(self) -> None:
        # HTTP server runs in background thread, nothing to close
        pass


class DatadogBackend(ObservabilityBackend):
    """
    Datadog backend for selftest metrics.

    Uses datadog API client to send metrics and events.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.api_endpoint = config.get("api_endpoint", "https://api.datadoghq.com")
        self.api_key = config.get("api_key") or os.environ.get("DATADOG_API_KEY")
        self.site = config.get("site", "datadoghq.com")
        self.tags = config.get("tags", [])
        self.metric_prefix = config.get("metric_prefix", "swarm.selftest")

        if not self.api_key:
            logger.warning("DATADOG_API_KEY not set, Datadog backend disabled")
            self.enabled = False
            self.dd = False
        else:
            # Try to import datadog library
            try:
                from datadog import api, initialize

                initialize(api_key=self.api_key, app_key=None, api_host=self.api_endpoint)
                self.dd_api = api
                self.dd = True
                logger.info("Datadog backend initialized")
            except ImportError:
                logger.warning("datadog library not installed, Datadog backend disabled")
                self.dd = False
                self.enabled = False

    def emit_run_started(self, run_id: str, tier: str, timestamp: float) -> None:
        if not self.enabled or not self.dd:
            return
        try:
            # Send event to Datadog
            title = f"Selftest run started: {run_id}"
            text = f"Tier: {tier}"
            tags = self.tags + [f"tier:{tier}", f"run_id:{run_id}"]
            self.dd_api.Event.create(title=title, text=text, tags=tags, alert_type="info")
        except Exception as e:
            logger.warning(f"Failed to emit run_started to Datadog: {e}")

    def emit_step_completed(self, step_id: str, duration_ms: int, result: str, tier: str) -> None:
        if not self.enabled or not self.dd:
            return
        try:
            tags = self.tags + [f"step_id:{step_id}", f"tier:{tier}", f"result:{result}"]
            # Send metric
            self.dd_api.Metric.send(
                metric=f"{self.metric_prefix}.step.duration",
                points=[(time.time(), duration_ms / 1000.0)],
                tags=tags,
            )
            self.dd_api.Metric.send(
                metric=f"{self.metric_prefix}.step.count",
                points=[(time.time(), 1)],
                tags=tags,
            )
        except Exception as e:
            logger.warning(f"Failed to emit step_completed to Datadog: {e}")

    def emit_step_failed(self, step_id: str, severity: str, error_message: str, tier: str) -> None:
        if not self.enabled or not self.dd:
            return
        try:
            tags = self.tags + [f"step_id:{step_id}", f"tier:{tier}", f"severity:{severity}"]
            # Send event
            title = f"Selftest step failed: {step_id}"
            text = f"Severity: {severity}\nError: {error_message[:200]}"
            self.dd_api.Event.create(title=title, text=text, tags=tags, alert_type="error")
            # Send metric
            self.dd_api.Metric.send(
                metric=f"{self.metric_prefix}.failure.count",
                points=[(time.time(), 1)],
                tags=tags,
            )
        except Exception as e:
            logger.warning(f"Failed to emit step_failed to Datadog: {e}")

    def emit_run_completed(self, run_id: str, result: str, duration_ms: int, summary: Dict[str, Any]) -> None:
        if not self.enabled or not self.dd:
            return
        try:
            tier = summary.get("mode", "strict")
            tags = self.tags + [f"run_id:{run_id}", f"tier:{tier}", f"result:{result}"]
            # Send metrics
            self.dd_api.Metric.send(
                metric=f"{self.metric_prefix}.run.duration",
                points=[(time.time(), duration_ms / 1000.0)],
                tags=tags,
            )
            self.dd_api.Metric.send(
                metric=f"{self.metric_prefix}.run.count",
                points=[(time.time(), 1)],
                tags=tags,
            )
            # Send summary metrics
            self.dd_api.Metric.send(
                metric=f"{self.metric_prefix}.steps.passed",
                points=[(time.time(), summary.get("passed", 0))],
                tags=tags,
            )
            self.dd_api.Metric.send(
                metric=f"{self.metric_prefix}.steps.failed",
                points=[(time.time(), summary.get("failed", 0))],
                tags=tags,
            )
            # Send event
            title = f"Selftest run completed: {result}"
            text = f"Run ID: {run_id}\nPassed: {summary.get('passed', 0)}\nFailed: {summary.get('failed', 0)}"
            alert_type = "success" if result == "PASS" else "error"
            self.dd_api.Event.create(title=title, text=text, tags=tags, alert_type=alert_type)
        except Exception as e:
            logger.warning(f"Failed to emit run_completed to Datadog: {e}")

    def close(self) -> None:
        # No cleanup needed for Datadog API
        pass


class CloudWatchBackend(ObservabilityBackend):
    """
    AWS CloudWatch backend for selftest metrics.

    Uses boto3 to send metrics to CloudWatch.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.namespace = config.get("namespace", "SelfTest")
        self.region = config.get("region") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self.dimensions_config = config.get("dimensions", [])
        self.storage_resolution = config.get("storage_resolution", 60)

        # Try to import boto3
        try:
            import boto3

            self.cloudwatch = boto3.client("cloudwatch", region_name=self.region)
            self.cw = True
            logger.info(f"CloudWatch backend initialized (region: {self.region})")
        except ImportError:
            logger.warning("boto3 not installed, CloudWatch backend disabled")
            self.cw = False
            self.enabled = False
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch client: {e}")
            self.cw = False
            self.enabled = False

    def _get_dimensions(self, additional: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """Build CloudWatch dimensions from config and additional tags."""
        dimensions = [{"Name": d["name"], "Value": d["value"]} for d in self.dimensions_config]
        if additional:
            for key, value in additional.items():
                dimensions.append({"Name": key, "Value": value})
        return dimensions

    def emit_run_started(self, run_id: str, tier: str, timestamp: float) -> None:
        if not self.enabled or not self.cw:
            return
        # No-op for CloudWatch (we track completion, not start)

    def emit_step_completed(self, step_id: str, duration_ms: int, result: str, tier: str) -> None:
        if not self.enabled or not self.cw:
            return
        try:
            dimensions = self._get_dimensions({"StepId": step_id, "Tier": tier, "Result": result})
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        "MetricName": "StepDuration",
                        "Dimensions": dimensions,
                        "Value": duration_ms / 1000.0,
                        "Unit": "Seconds",
                        "StorageResolution": self.storage_resolution,
                    },
                    {
                        "MetricName": "StepCount",
                        "Dimensions": dimensions,
                        "Value": 1,
                        "Unit": "Count",
                        "StorageResolution": self.storage_resolution,
                    },
                ],
            )
        except Exception as e:
            logger.warning(f"Failed to emit step_completed to CloudWatch: {e}")

    def emit_step_failed(self, step_id: str, severity: str, error_message: str, tier: str) -> None:
        if not self.enabled or not self.cw:
            return
        try:
            dimensions = self._get_dimensions({"StepId": step_id, "Tier": tier, "Severity": severity})
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        "MetricName": "FailureCount",
                        "Dimensions": dimensions,
                        "Value": 1,
                        "Unit": "Count",
                        "StorageResolution": self.storage_resolution,
                    }
                ],
            )
        except Exception as e:
            logger.warning(f"Failed to emit step_failed to CloudWatch: {e}")

    def emit_run_completed(self, run_id: str, result: str, duration_ms: int, summary: Dict[str, Any]) -> None:
        if not self.enabled or not self.cw:
            return
        try:
            tier = summary.get("mode", "strict")
            dimensions = self._get_dimensions({"RunId": run_id, "Tier": tier, "Result": result})
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        "MetricName": "RunDuration",
                        "Dimensions": dimensions,
                        "Value": duration_ms / 1000.0,
                        "Unit": "Seconds",
                        "StorageResolution": self.storage_resolution,
                    },
                    {
                        "MetricName": "RunCount",
                        "Dimensions": dimensions,
                        "Value": 1,
                        "Unit": "Count",
                        "StorageResolution": self.storage_resolution,
                    },
                    {
                        "MetricName": "StepsPassed",
                        "Dimensions": dimensions,
                        "Value": summary.get("passed", 0),
                        "Unit": "Count",
                        "StorageResolution": self.storage_resolution,
                    },
                    {
                        "MetricName": "StepsFailed",
                        "Dimensions": dimensions,
                        "Value": summary.get("failed", 0),
                        "Unit": "Count",
                        "StorageResolution": self.storage_resolution,
                    },
                ],
            )
        except Exception as e:
            logger.warning(f"Failed to emit run_completed to CloudWatch: {e}")

    def close(self) -> None:
        # No cleanup needed for CloudWatch client
        pass


class LogBackend(ObservabilityBackend):
    """
    Structured logging backend for selftest events.

    Writes JSON lines or text to stdout/stderr/file.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.format = config.get("format", "json")
        self.output = config.get("output", "stdout")
        self.level = config.get("level", "INFO")
        self.include_output = config.get("include_output", False)
        self.timestamp_format = config.get("timestamp_format", "iso8601")

        # Open output stream
        if self.output == "stdout":
            self.stream = sys.stdout
        elif self.output == "stderr":
            self.stream = sys.stderr
        else:
            # File path
            try:
                self.stream = open(self.output, "a")
            except Exception as e:
                logger.warning(f"Failed to open log file {self.output}: {e}, falling back to stdout")
                self.stream = sys.stdout

    def _get_timestamp(self) -> str:
        """Get formatted timestamp."""
        if self.timestamp_format == "unix":
            return str(time.time())
        else:
            return datetime.now(timezone.utc).isoformat()

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Write event to log stream."""
        event = {
            "timestamp": self._get_timestamp(),
            "event_type": event_type,
            **data,
        }

        if self.format == "json":
            self.stream.write(json.dumps(event) + "\n")
        else:
            # Text format
            parts = [f"{k}={v}" for k, v in event.items()]
            self.stream.write(" ".join(parts) + "\n")

        self.stream.flush()

    def emit_run_started(self, run_id: str, tier: str, timestamp: float) -> None:
        if not self.enabled:
            return
        self._log_event("run_started", {"run_id": run_id, "tier": tier})

    def emit_step_completed(self, step_id: str, duration_ms: int, result: str, tier: str) -> None:
        if not self.enabled:
            return
        self._log_event("step_completed", {"step_id": step_id, "duration_ms": duration_ms, "result": result, "tier": tier})

    def emit_step_failed(self, step_id: str, severity: str, error_message: str, tier: str) -> None:
        if not self.enabled:
            return
        data = {"step_id": step_id, "severity": severity, "tier": tier}
        if self.include_output:
            data["error_message"] = error_message[:500]  # Truncate
        self._log_event("step_failed", data)

    def emit_run_completed(self, run_id: str, result: str, duration_ms: int, summary: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        self._log_event(
            "run_completed",
            {
                "run_id": run_id,
                "result": result,
                "duration_ms": duration_ms,
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
            },
        )

    def close(self) -> None:
        if self.stream not in (sys.stdout, sys.stderr):
            self.stream.close()


class BackendManager:
    """
    Manages multiple observability backends.

    Loads config, initializes backends, and forwards events to all enabled backends.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize BackendManager.

        Args:
            config_path: Path to observability_backends.yaml config file.
                        If None, uses default location: swarm/config/observability_backends.yaml
        """
        if config_path is None:
            # Default config path
            repo_root = Path(__file__).resolve().parents[2]
            config_path = repo_root / "swarm" / "config" / "observability_backends.yaml"

        self.config_path = config_path
        self.config = self._load_config()
        self.backends: List[ObservabilityBackend] = []
        self.global_enabled = self.config.get("global", {}).get("enabled", True)
        self.strict_mode = self.config.get("global", {}).get("strict_mode", False)

        if self.global_enabled:
            self._initialize_backends()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                return load_yaml(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return {"backends": {}, "global": {"enabled": True, "strict_mode": False}}
        except Exception as e:
            logger.warning(f"Failed to load config from {self.config_path}: {e}, using defaults")
            return {"backends": {}, "global": {"enabled": True, "strict_mode": False}}

    def _initialize_backends(self) -> None:
        """Initialize all enabled backends."""
        backends_config = self.config.get("backends", {})

        # Prometheus
        if backends_config.get("prometheus", {}).get("enabled", False):
            try:
                backend = PrometheusBackend(backends_config["prometheus"], strict_mode=self.strict_mode)
                if backend.enabled:
                    self.backends.append(backend)
                    logger.info("Prometheus backend initialized")
            except Exception as e:
                msg = f"Failed to initialize Prometheus backend: {e}"
                if self.strict_mode:
                    raise RuntimeError(msg) from e
                logger.warning(msg)

        # Datadog
        if backends_config.get("datadog", {}).get("enabled", False):
            try:
                backend = DatadogBackend(backends_config["datadog"])
                if backend.enabled:
                    self.backends.append(backend)
                    logger.info("Datadog backend initialized")
            except Exception as e:
                msg = f"Failed to initialize Datadog backend: {e}"
                if self.strict_mode:
                    raise RuntimeError(msg)
                logger.warning(msg)

        # CloudWatch
        if backends_config.get("cloudwatch", {}).get("enabled", False):
            try:
                backend = CloudWatchBackend(backends_config["cloudwatch"])
                if backend.enabled:
                    self.backends.append(backend)
                    logger.info("CloudWatch backend initialized")
            except Exception as e:
                msg = f"Failed to initialize CloudWatch backend: {e}"
                if self.strict_mode:
                    raise RuntimeError(msg)
                logger.warning(msg)

        # Logs (always enabled by default)
        if backends_config.get("logs", {}).get("enabled", True):
            try:
                backend = LogBackend(backends_config.get("logs", {}))
                if backend.enabled:
                    self.backends.append(backend)
                    logger.info("Log backend initialized")
            except Exception as e:
                msg = f"Failed to initialize Log backend: {e}"
                if self.strict_mode:
                    raise RuntimeError(msg)
                logger.warning(msg)

    def emit_run_started(self, run_id: str, tier: str, timestamp: float = None) -> None:
        """Forward run_started event to all backends."""
        if timestamp is None:
            timestamp = time.time()

        for backend in self.backends:
            try:
                backend.emit_run_started(run_id, tier, timestamp)
            except Exception as e:
                logger.warning(f"Backend {backend.__class__.__name__} failed to emit run_started: {e}")

    def emit_step_completed(self, step_id: str, duration_ms: int, result: str, tier: str) -> None:
        """Forward step_completed event to all backends."""
        for backend in self.backends:
            try:
                backend.emit_step_completed(step_id, duration_ms, result, tier)
            except Exception as e:
                logger.warning(f"Backend {backend.__class__.__name__} failed to emit step_completed: {e}")

    def emit_step_failed(self, step_id: str, severity: str, error_message: str, tier: str) -> None:
        """Forward step_failed event to all backends."""
        for backend in self.backends:
            try:
                backend.emit_step_failed(step_id, severity, error_message, tier)
            except Exception as e:
                logger.warning(f"Backend {backend.__class__.__name__} failed to emit step_failed: {e}")

    def emit_run_completed(self, run_id: str, result: str, duration_ms: int, summary: Dict[str, Any]) -> None:
        """Forward run_completed event to all backends."""
        for backend in self.backends:
            try:
                backend.emit_run_completed(run_id, result, duration_ms, summary)
            except Exception as e:
                logger.warning(f"Backend {backend.__class__.__name__} failed to emit run_completed: {e}")

    def close(self) -> None:
        """Close all backends."""
        for backend in self.backends:
            try:
                backend.close()
            except Exception as e:
                logger.warning(f"Backend {backend.__class__.__name__} failed to close: {e}")
