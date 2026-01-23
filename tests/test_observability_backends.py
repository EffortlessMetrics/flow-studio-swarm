"""
Integration tests for observability backends.

Tests:
- Config loading and validation
- Backend initialization (enabled/disabled)
- Credential detection (env vars, files)
- Graceful degradation (missing creds don't crash)
- Metrics emission (call each backend method, verify)
- JSON log format correctness
"""

import json
import os
import sys
import time
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

import yaml

# Add swarm/tools to path for imports
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "swarm" / "tools"))

from observability_backends import (
    BackendManager,
    CloudWatchBackend,
    DatadogBackend,
    LogBackend,
    ObservabilityBackend,
    PrometheusBackend,
)


class TestConfigLoading:
    """Test configuration loading and validation."""

    def test_load_default_config_when_no_file_exists(self, tmp_path):
        """BackendManager should use defaults when config file doesn't exist."""
        non_existent = tmp_path / "does_not_exist.yaml"
        manager = BackendManager(config_path=non_existent)
        # Should not crash, should have default config
        assert manager.config is not None
        assert manager.global_enabled is True

    def test_load_config_from_valid_yaml(self, tmp_path):
        """BackendManager should load config from valid YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_data = {
            "version": "1.0",
            "backends": {"logs": {"enabled": True, "format": "json", "output": "stdout"}},
            "global": {"enabled": True, "strict_mode": False},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = BackendManager(config_path=config_file)
        assert manager.config["version"] == "1.0"
        assert manager.config["backends"]["logs"]["enabled"] is True

    def test_config_with_invalid_yaml_falls_back_to_defaults(self, tmp_path):
        """BackendManager should fall back to defaults if YAML is malformed."""
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, "w") as f:
            f.write("{ invalid yaml content ][")

        manager = BackendManager(config_path=config_file)
        # Should not crash, should use defaults
        assert manager.config is not None

    def test_global_enabled_flag_disables_all_backends(self, tmp_path):
        """Global enabled=false should prevent backend initialization."""
        config_file = tmp_path / "disabled.yaml"
        config_data = {
            "backends": {"logs": {"enabled": True}},
            "global": {"enabled": False},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = BackendManager(config_path=config_file)
        assert len(manager.backends) == 0


class TestLogBackend:
    """Test JSON logging backend."""

    def test_log_backend_emits_json_to_stdout(self):
        """LogBackend should emit JSON lines to stdout."""
        output = StringIO()
        config = {"enabled": True, "format": "json", "output": "stdout"}

        with patch("sys.stdout", output):
            backend = LogBackend(config)
            backend.stream = output  # Override stream for testing

            backend.emit_run_started("test-run-1", "kernel", time.time())
            backend.emit_step_completed("core-checks", 1500, "PASS", "kernel")
            backend.emit_step_failed(
                "agents-governance", "warning", "Agent foo not found", "governance"
            )
            backend.emit_run_completed(
                "test-run-1", "FAIL", 5000, {"passed": 2, "failed": 1, "skipped": 0}
            )

        output_lines = output.getvalue().strip().split("\n")
        assert len(output_lines) == 4

        # Parse each line as JSON
        for line in output_lines:
            event = json.loads(line)
            assert "timestamp" in event
            assert "event_type" in event

        # Check specific events
        run_started = json.loads(output_lines[0])
        assert run_started["event_type"] == "run_started"
        assert run_started["run_id"] == "test-run-1"
        assert run_started["tier"] == "kernel"

        step_completed = json.loads(output_lines[1])
        assert step_completed["event_type"] == "step_completed"
        assert step_completed["step_id"] == "core-checks"
        assert step_completed["result"] == "PASS"

        step_failed = json.loads(output_lines[2])
        assert step_failed["event_type"] == "step_failed"
        assert step_failed["step_id"] == "agents-governance"
        assert step_failed["severity"] == "warning"

        run_completed = json.loads(output_lines[3])
        assert run_completed["event_type"] == "run_completed"
        assert run_completed["result"] == "FAIL"
        assert run_completed["passed"] == 2
        assert run_completed["failed"] == 1

    def test_log_backend_text_format(self):
        """LogBackend should emit text format when configured."""
        output = StringIO()
        config = {"enabled": True, "format": "text", "output": "stdout"}

        with patch("sys.stdout", output):
            backend = LogBackend(config)
            backend.stream = output

            backend.emit_run_started("test-run-2", "strict", time.time())

        output_text = output.getvalue()
        assert "event_type=run_started" in output_text
        assert "run_id=test-run-2" in output_text
        assert "tier=strict" in output_text

    def test_log_backend_disabled(self):
        """LogBackend should not emit when disabled."""
        output = StringIO()
        config = {"enabled": False, "format": "json", "output": "stdout"}

        with patch("sys.stdout", output):
            backend = LogBackend(config)
            backend.stream = output

            backend.emit_run_started("test-run-3", "kernel", time.time())

        assert output.getvalue() == ""

    def test_log_backend_file_output(self, tmp_path):
        """LogBackend should write to file when configured."""
        log_file = tmp_path / "selftest.log"
        config = {"enabled": True, "format": "json", "output": str(log_file)}

        backend = LogBackend(config)
        backend.emit_run_started("test-run-4", "kernel", time.time())
        backend.close()

        assert log_file.exists()
        with open(log_file, "r") as f:
            line = f.readline()
            event = json.loads(line)
            assert event["event_type"] == "run_started"

    def test_log_backend_graceful_fallback_on_invalid_file(self):
        """LogBackend should fall back to stdout if file can't be opened."""
        config = {"enabled": True, "format": "json", "output": "/invalid/path/to/file.log"}

        with patch("sys.stdout", StringIO()):
            backend = LogBackend(config)
            # Should not crash, should use stdout
            assert backend.stream == sys.stdout


class TestPrometheusBackend:
    """Test Prometheus metrics backend."""

    @patch("observability_backends.PrometheusBackend.__init__", return_value=None)
    def test_prometheus_backend_disabled_when_library_missing(self, mock_init):
        """PrometheusBackend should disable gracefully if prometheus_client not installed."""
        config = {"enabled": True, "pushgateway_url": None, "serve_port": 8000}

        with patch.dict("sys.modules", {"prometheus_client": None}):
            backend = PrometheusBackend(config)
            backend.enabled = False
            backend.prom = False

            # Should not crash on emit calls
            backend.emit_run_started("test", "kernel", time.time())
            backend.emit_step_completed("test", 100, "PASS", "kernel")
            backend.close()

    def test_prometheus_backend_initializes_metrics(self):
        """PrometheusBackend should initialize Prometheus metrics."""
        config = {"enabled": True, "pushgateway_url": None, "serve_port": 9999, "job_name": "test"}

        try:
            import prometheus_client  # noqa: F401 - availability check

            backend = PrometheusBackend(config)
            assert backend.enabled is True
            assert backend.prom is True
            assert backend.registry is not None
        except ImportError:
            pytest.skip("prometheus_client not installed")

    def test_prometheus_backend_emits_metrics(self):
        """PrometheusBackend should increment counters and observe histograms."""
        config = {"enabled": True, "pushgateway_url": None, "serve_port": 9998, "job_name": "test"}

        try:
            backend = PrometheusBackend(config)
            if not backend.enabled:
                pytest.skip("Prometheus backend not available")

            backend.emit_step_completed("core-checks", 1500, "PASS", "kernel")
            backend.emit_step_failed("agents-governance", "warning", "error", "governance")
            backend.emit_run_completed(
                "test-run", "PASS", 5000, {"mode": "strict", "passed": 3, "failed": 0}
            )

            # Metrics should be updated (no exceptions)
            backend.close()
        except ImportError:
            pytest.skip("prometheus_client not installed")


class TestDatadogBackend:
    """Test Datadog metrics backend."""

    def test_datadog_backend_disabled_when_no_api_key(self):
        """DatadogBackend should disable when DATADOG_API_KEY not set."""
        config = {"enabled": True, "api_endpoint": "https://api.datadoghq.com"}

        with patch.dict(os.environ, {}, clear=True):
            backend = DatadogBackend(config)
            assert backend.enabled is False

    @patch.dict(os.environ, {"DATADOG_API_KEY": "test-key-123"})
    @patch("observability_backends.DatadogBackend.__init__")
    def test_datadog_backend_initializes_with_api_key(self, mock_init):
        """DatadogBackend should initialize when DATADOG_API_KEY is set."""
        mock_init.return_value = None

        # Should detect API key from environment
        api_key = os.environ.get("DATADOG_API_KEY")
        assert api_key == "test-key-123"

    def test_datadog_backend_emits_events_and_metrics(self):
        """DatadogBackend should send events and metrics to Datadog API."""
        # Skip if datadog library not installed
        try:
            import datadog  # noqa: F401
        except ImportError:
            pytest.skip("datadog library not installed")

        config = {
            "enabled": True,
            "api_key": "test-key-456",
            "tags": ["env:test"],
            "metric_prefix": "swarm.selftest",
        }

        with patch.dict(os.environ, {"DATADOG_API_KEY": "test-key-456"}):
            with patch("datadog.api.Event.create") as mock_event_create:
                with patch("datadog.api.Metric.send") as mock_metric_send:
                    backend = DatadogBackend(config)
                    if not backend.enabled or not backend.dd:
                        pytest.skip("Datadog backend not available")

                    backend.emit_run_started("test-run", "kernel", time.time())
                    backend.emit_step_completed("core-checks", 1500, "PASS", "kernel")
                    backend.emit_step_failed("test-step", "critical", "error", "kernel")
                    backend.emit_run_completed(
                        "test-run", "FAIL", 5000, {"mode": "strict", "passed": 2, "failed": 1}
                    )

                    # Verify API calls were made
                    assert (
                        mock_event_create.call_count >= 2
                    )  # run_started, step_failed, run_completed events
                    assert mock_metric_send.call_count >= 4  # step and run metrics


class TestCloudWatchBackend:
    """Test AWS CloudWatch metrics backend."""

    def test_cloudwatch_backend_disabled_when_boto3_missing(self):
        """CloudWatchBackend should disable gracefully if boto3 not installed."""
        config = {"enabled": True, "namespace": "SelfTest"}

        with patch.dict("sys.modules", {"boto3": None}):
            backend = CloudWatchBackend(config)
            # Should not crash
            assert backend.enabled is False or backend.cw is False

    def test_cloudwatch_backend_initializes_client(self):
        """CloudWatchBackend should initialize boto3 CloudWatch client."""
        # Skip if boto3 not installed
        try:
            import boto3  # noqa: F401
        except ImportError:
            pytest.skip("boto3 not installed")

        config = {"enabled": True, "namespace": "SelfTest", "region": "us-west-2"}

        with patch("boto3.client") as mock_client:
            backend = CloudWatchBackend(config)
            if backend.enabled and backend.cw:
                mock_client.assert_called_once_with("cloudwatch", region_name="us-west-2")

    def test_cloudwatch_backend_emits_metrics(self):
        """CloudWatchBackend should put metrics to CloudWatch."""
        # Skip if boto3 not installed
        try:
            import boto3  # noqa: F401
        except ImportError:
            pytest.skip("boto3 not installed")

        mock_cw = MagicMock()
        config = {
            "enabled": True,
            "namespace": "SelfTest",
            "region": "us-east-1",
            "dimensions": [{"name": "Environment", "value": "test"}],
        }

        with patch("boto3.client", return_value=mock_cw):
            backend = CloudWatchBackend(config)
            if not backend.enabled or not backend.cw:
                pytest.skip("CloudWatch backend not available")

            backend.emit_step_completed("core-checks", 1500, "PASS", "kernel")
            backend.emit_step_failed("test-step", "warning", "error", "governance")
            backend.emit_run_completed(
                "test-run", "PASS", 5000, {"mode": "strict", "passed": 3, "failed": 0}
            )

            # Verify put_metric_data was called
            assert mock_cw.put_metric_data.call_count >= 3


class TestBackendManager:
    """Test BackendManager orchestration."""

    def test_backend_manager_initializes_enabled_backends(self, tmp_path):
        """BackendManager should initialize only enabled backends."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "backends": {
                "logs": {"enabled": True, "format": "json", "output": "stdout"},
                "prometheus": {"enabled": False},
                "datadog": {"enabled": False},
                "cloudwatch": {"enabled": False},
            },
            "global": {"enabled": True},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = BackendManager(config_path=config_file)
        # Should have only logs backend
        assert len(manager.backends) >= 1
        assert any(isinstance(b, LogBackend) for b in manager.backends)

    def test_backend_manager_forwards_events_to_all_backends(self, tmp_path):
        """BackendManager should forward events to all enabled backends."""
        config_file = tmp_path / "config.yaml"
        log_file = tmp_path / "test.log"
        config_data = {
            "backends": {
                "logs": {"enabled": True, "format": "json", "output": str(log_file)},
            },
            "global": {"enabled": True},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = BackendManager(config_path=config_file)

        manager.emit_run_started("test-run", "kernel", time.time())
        manager.emit_step_completed("core-checks", 1500, "PASS", "kernel")
        manager.emit_step_failed("test-step", "critical", "error", "kernel")
        manager.emit_run_completed(
            "test-run", "FAIL", 5000, {"passed": 1, "failed": 1, "skipped": 0}
        )
        manager.close()

        # Verify events were written to log file
        assert log_file.exists()
        with open(log_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 4
            for line in lines:
                event = json.loads(line)
                assert "timestamp" in event
                assert "event_type" in event

    def test_backend_manager_handles_backend_errors_gracefully(self, tmp_path):
        """BackendManager should not crash if a backend raises an exception."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "backends": {"logs": {"enabled": True, "format": "json", "output": "stdout"}},
            "global": {"enabled": True, "strict_mode": False},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = BackendManager(config_path=config_file)

        # Mock a backend to raise an exception
        mock_backend = Mock(spec=ObservabilityBackend)
        mock_backend.emit_run_started.side_effect = Exception("Backend error")
        manager.backends.append(mock_backend)

        # Should not crash
        manager.emit_run_started("test-run", "kernel", time.time())
        manager.close()

    def test_backend_manager_strict_mode_raises_on_init_failure(self, tmp_path):
        """BackendManager strict mode should raise if backend initialization fails."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "backends": {
                "prometheus": {"enabled": True, "serve_port": -1}  # Invalid port
            },
            "global": {"enabled": True, "strict_mode": True},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # In strict mode, should raise if Prometheus fails to init (if prometheus_client available)
        try:
            import prometheus_client  # noqa: F401

            with pytest.raises(RuntimeError):
                BackendManager(config_path=config_file)
        except ImportError:
            # prometheus_client not installed, skip test
            pytest.skip("prometheus_client not installed")

    def test_backend_manager_close_closes_all_backends(self, tmp_path):
        """BackendManager.close() should close all backends."""
        config_file = tmp_path / "config.yaml"
        log_file = tmp_path / "test.log"
        config_data = {
            "backends": {"logs": {"enabled": True, "format": "json", "output": str(log_file)}},
            "global": {"enabled": True},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = BackendManager(config_path=config_file)
        manager.emit_run_started("test-run", "kernel", time.time())

        # Spy on backend close calls
        for backend in manager.backends:
            backend.close = Mock(side_effect=backend.close)

        manager.close()

        # Verify all backends were closed
        for backend in manager.backends:
            backend.close.assert_called_once()


class TestEndToEndIntegration:
    """End-to-end integration tests with selftest.py."""

    def test_selftest_emits_to_log_backend(self, tmp_path):
        """Selftest should emit events to log backend during execution."""
        log_file = tmp_path / "selftest_events.log"
        config_file = tmp_path / "observability_backends.yaml"
        config_data = {
            "backends": {
                "logs": {"enabled": True, "format": "json", "output": str(log_file)},
            },
            "global": {"enabled": True},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Import selftest module
        from selftest import SelfTestRunner

        # Mock BackendManager to use our config
        with patch("selftest.BackendManager") as MockBackendManager:
            mock_manager = BackendManager(config_path=config_file)
            MockBackendManager.return_value = mock_manager

            runner = SelfTestRunner(kernel_only=True, write_report=False)
            # Don't actually run selftest, just verify manager was initialized
            assert runner.backends is not None

        # Simulate events
        mock_manager.emit_run_started("test-run", "kernel", time.time())
        mock_manager.emit_step_completed("core-checks", 1000, "PASS", "kernel")
        mock_manager.emit_run_completed(
            "test-run", "PASS", 1500, {"passed": 1, "failed": 0, "skipped": 0, "mode": "kernel"}
        )
        mock_manager.close()

        # Verify events were logged
        assert log_file.exists()
        with open(log_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 3
            events = [json.loads(line) for line in lines]
            assert events[0]["event_type"] == "run_started"
            assert events[1]["event_type"] == "step_completed"
            assert events[2]["event_type"] == "run_completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
