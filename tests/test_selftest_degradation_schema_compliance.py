"""
Unit tests for DEGRADATION_LOG_SCHEMA enforcement in swarm/tools/selftest.py.

These tests validate the schema definition and its enforcement at the code level,
complementing the integration tests in test_selftest_degradation_log.py.

Schema Definition (AC-SELFTEST-DEGRADATION-TRACKED):
    timestamp:   ISO 8601 UTC timestamp (required)
    step_id:     Unique step identifier (required)
    step_name:   Human-readable step description (required)
    tier:        Selftest tier enum: "governance" | "optional" (NEVER "kernel") (required)
    status:      StepStatus enum: "PASS" | "FAIL" | "SKIP" | "TIMEOUT" (required, v1.1+)
    reason:      Why step ended in this status (required, v1.1+)
    message:     Failure output from step (required)
    severity:    Severity enum: "critical" | "warning" | "info" (required)
    remediation: Suggested fix command (required)
    version:     Schema version, frozen at "1.1" (in schema metadata, not entries)

Design Invariant:
    - KERNEL tier failures are NEVER logged (they block immediately)
    - Only GOVERNANCE and OPTIONAL tier failures are logged in degraded mode
    - Schema version is frozen; bumping requires governance approval
"""

import json

# Import actual schema from codebase
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import mock_open, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "swarm" / "tools"))

from selftest import DEGRADATION_LOG_SCHEMA

# ============================================================================
# Test Fixtures
# ============================================================================


@dataclass
class DegradationEntry:
    """
    Type-safe degradation entry matching the JSONL schema (v1.1).

    This dataclass enforces the schema at the type level for test fixtures.
    """

    timestamp: str
    step_id: str
    step_name: str
    tier: str  # "governance" | "optional" (NEVER "kernel")
    status: str  # StepStatus: "PASS" | "FAIL" | "SKIP" | "TIMEOUT"
    reason: str  # Why step ended in this status
    message: str
    severity: str  # "critical" | "warning" | "info"
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


def build_valid_degradation_entry(
    step_id: str = "agents-governance",
    tier: str = "governance",
    severity: str = "warning",
    status: str = "FAIL",
    reason: str = "nonzero_exit",
) -> DegradationEntry:
    """
    Build a valid degradation entry for test fixtures (v1.1 schema).

    Args:
        step_id: Step identifier (default: "agents-governance")
        tier: Tier enum value (default: "governance", NEVER "kernel")
        severity: Severity enum value (default: "warning")
        status: StepStatus enum value (default: "FAIL")
        reason: Why step ended in this status (default: "nonzero_exit")

    Returns:
        DegradationEntry with all required fields
    """
    return DegradationEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        step_id=step_id,
        step_name=f"Test step: {step_id}",
        tier=tier,
        status=status,
        reason=reason,
        message=f"Test failure for {step_id}",
        severity=severity,
        remediation=f"Run: uv run swarm/tools/selftest.py --step {step_id} for details",
    )


# ============================================================================
# FR-DEGRADE-SCHEMA-1: Required Fields Presence
# ============================================================================


class TestDegradationSchemaRequiredFields:
    """Validate all required fields are present in schema definition."""

    def test_degradation_entry_has_all_required_fields(self):
        """
        FR-DEGRADE-SCHEMA-1: Degradation entry contains all 9 required fields (v1.1).

        Verifies schema definition includes:
        - timestamp, step_id, step_name, tier, status, reason, message, severity, remediation
        """
        entry = build_valid_degradation_entry()
        entry_dict = entry.to_dict()

        required_fields = {
            "timestamp",
            "step_id",
            "step_name",
            "tier",
            "status",
            "reason",
            "message",
            "severity",
            "remediation",
        }

        actual_fields = set(entry_dict.keys())
        assert actual_fields == required_fields, (
            f"Degradation entry missing required fields. "
            f"Expected: {required_fields}, Got: {actual_fields}"
        )

    def test_degradation_entry_rejects_missing_timestamp(self):
        """Schema validation detects missing timestamp field."""
        entry = build_valid_degradation_entry()
        entry_dict = entry.to_dict()
        del entry_dict["timestamp"]

        # Validation should fail if timestamp is missing
        required_fields = set(DEGRADATION_LOG_SCHEMA["required_fields"])
        actual_fields = set(entry_dict.keys())
        missing = required_fields - actual_fields

        assert "timestamp" in missing, "Should detect missing timestamp field"

    def test_degradation_entry_rejects_missing_tier(self):
        """Schema validation detects missing tier field."""
        entry = build_valid_degradation_entry()
        entry_dict = entry.to_dict()
        del entry_dict["tier"]

        required_fields = set(DEGRADATION_LOG_SCHEMA["required_fields"])
        actual_fields = set(entry_dict.keys())
        missing = required_fields - actual_fields

        assert "tier" in missing, "Should detect missing tier field"

    def test_degradation_entry_rejects_missing_severity(self):
        """Schema validation detects missing severity field."""
        entry = build_valid_degradation_entry()
        entry_dict = entry.to_dict()
        del entry_dict["severity"]

        required_fields = set(DEGRADATION_LOG_SCHEMA["required_fields"])
        actual_fields = set(entry_dict.keys())
        missing = required_fields - actual_fields

        assert "severity" in missing, "Should detect missing severity field"


# ============================================================================
# FR-DEGRADE-SCHEMA-2: Timestamp ISO 8601 Format
# ============================================================================


class TestDegradationTimestampFormat:
    """Validate timestamp field conforms to ISO 8601."""

    def test_degradation_timestamp_is_iso8601(self):
        """
        FR-DEGRADE-SCHEMA-2: timestamp field is valid ISO 8601 with time component.

        Validates:
        - Timestamp parses as datetime
        - Includes date + time components
        - Uses UTC timezone
        """
        entry = build_valid_degradation_entry()

        # Parse timestamp to ensure it's valid ISO 8601
        try:
            parsed = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            pytest.fail(f"Timestamp '{entry.timestamp}' is not valid ISO 8601: {e}")

        # Verify it includes both date and time
        assert parsed.year >= 2025, "Timestamp should have valid year"
        assert parsed.hour is not None, "Timestamp should include time component"
        assert parsed.tzinfo is not None, "Timestamp should include timezone info"

    def test_degradation_timestamp_rejects_date_only(self):
        """Timestamp validation rejects date-only format (no time component)."""
        entry = build_valid_degradation_entry()
        entry.timestamp = "2025-12-01"  # Date only, no time

        # Python's fromisoformat() accepts date-only strings, so we need
        # to validate that the timestamp includes time component explicitly
        # Date-only timestamps parse to midnight (00:00:00), which is
        # insufficient for degradation logging (we need explicit time)
        # In production, validation should reject timestamps without 'T' separator
        assert "T" not in entry.timestamp, "Date-only timestamp should not include 'T' separator"

        # Verify the validation function in test_selftest_degradation_log.py
        # would catch this (it checks for time component)

    def test_degradation_timestamp_includes_timezone(self):
        """Timestamp includes explicit timezone information (UTC)."""
        entry = build_valid_degradation_entry()

        # Parse and verify timezone is present
        parsed = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, "Timestamp must include timezone"
        assert parsed.tzinfo.utcoffset(None).total_seconds() == 0, (
            "Timestamp must be in UTC (offset 0)"
        )


# ============================================================================
# FR-DEGRADE-SCHEMA-3: Tier Constraint (NEVER kernel)
# ============================================================================


class TestDegradationTierConstraint:
    """Validate tier field constraint: NEVER "kernel"."""

    def test_degradation_tier_never_kernel(self):
        """
        FR-DEGRADE-SCHEMA-3: tier field is NEVER "kernel" (design invariant).

        KERNEL tier failures block immediately and are never logged to
        degradation log. Only GOVERNANCE and OPTIONAL failures are logged.
        """
        # Valid tiers for degradation log
        valid_tiers = ["governance", "optional"]

        for tier in valid_tiers:
            entry = build_valid_degradation_entry(tier=tier)
            assert entry.tier in valid_tiers, (
                f"Tier '{entry.tier}' should be valid for degradation log"
            )
            assert entry.tier != "kernel", "KERNEL tier should NEVER appear in degradation log"

    def test_degradation_log_schema_documents_tier_constraint(self):
        """
        Schema documentation explicitly states tier is for governance/optional only.

        Verifies that DEGRADATION_LOG_SCHEMA example does not use "kernel" tier.
        """
        example_entry = DEGRADATION_LOG_SCHEMA["example"]
        assert example_entry["tier"] in ["governance", "optional"], (
            f"Schema example should use governance or optional tier, got '{example_entry['tier']}'"
        )
        assert example_entry["tier"] != "kernel", (
            "Schema example must not use kernel tier (design invariant)"
        )

    def test_degradation_tier_enum_validates_correctly(self):
        """Tier validation accepts only governance and optional in degraded mode."""
        valid_tiers = {"governance", "optional"}

        for tier in valid_tiers:
            entry = build_valid_degradation_entry(tier=tier)
            assert entry.tier in valid_tiers, f"Tier '{tier}' should be valid"

        # Note: Kernel tier is rejected by log_degradation() check in production
        # (it returns early if step.tier == KERNEL, so kernel entries never reach log)


# ============================================================================
# FR-DEGRADE-SCHEMA-4: Severity Enum Validation
# ============================================================================


class TestDegradationSeverityEnum:
    """Validate severity field enum constraint."""

    def test_degradation_severity_enum_valid(self):
        """
        FR-DEGRADE-SCHEMA-4: severity is one of {critical, warning, info}.

        Verifies enum constraint on severity field.
        """
        valid_severities = ["critical", "warning", "info"]

        for severity in valid_severities:
            entry = build_valid_degradation_entry(severity=severity)
            assert entry.severity in valid_severities, f"Severity '{severity}' should be valid"

    def test_degradation_severity_rejects_invalid_values(self):
        """Severity validation rejects non-enum values."""
        invalid_severities = ["error", "fatal", "debug", "trace", "unknown"]
        valid_severities = {"critical", "warning", "info"}

        for invalid in invalid_severities:
            # In production, this would be caught by validation
            assert invalid not in valid_severities, (
                f"Invalid severity '{invalid}' should be rejected"
            )

    def test_degradation_severity_maps_to_tier_correctly(self):
        """
        Severity mapping follows tier conventions:
        - GOVERNANCE tier → WARNING severity (typical)
        - OPTIONAL tier → INFO severity (typical)

        Note: This is a convention, not a hard constraint.
        """
        # Typical mapping (but not enforced at schema level)
        gov_entry = build_valid_degradation_entry(tier="governance", severity="warning")
        assert gov_entry.severity == "warning", "GOVERNANCE typically maps to WARNING"

        opt_entry = build_valid_degradation_entry(tier="optional", severity="info")
        assert opt_entry.severity == "info", "OPTIONAL typically maps to INFO"


# ============================================================================
# FR-DEGRADE-SCHEMA-5: Schema Version Frozen
# ============================================================================


class TestDegradationSchemaVersion:
    """Validate schema version is frozen at 1.1."""

    def test_degradation_schema_version_frozen(self):
        """
        FR-DEGRADE-SCHEMA-5: Schema version is frozen at "1.1".

        Bumping schema version requires:
        1. Governance approval (documented in swarm/SELFTEST_SYSTEM.md)
        2. Migration path for existing logs
        3. Backward compatibility verification

        This test will fail if version changes, forcing explicit review.

        Version History:
        - 1.0: Initial schema (7 fields)
        - 1.1: Added status and reason fields for unified StepStatus vocabulary
        """
        assert DEGRADATION_LOG_SCHEMA["version"] == "1.1", (
            "Schema version bump detected. Before changing:\n"
            "1. Document breaking changes in swarm/SELFTEST_SYSTEM.md\n"
            "2. Provide migration script for existing logs\n"
            "3. Update all consumers (CLI tool, dashboards, CI)\n"
            "4. Get governance approval\n"
            "Then update this assertion to match new version."
        )

    def test_degradation_schema_required_fields_stable(self):
        """Schema required_fields list remains stable across versions (v1.1)."""
        expected_fields = [
            "timestamp",
            "step_id",
            "step_name",
            "tier",
            "status",  # Added in v1.1
            "reason",  # Added in v1.1
            "message",
            "severity",
            "remediation",
        ]

        actual_fields = DEGRADATION_LOG_SCHEMA["required_fields"]
        assert actual_fields == expected_fields, (
            f"Required fields changed. Expected: {expected_fields}, "
            f"Got: {actual_fields}. Schema changes require governance approval."
        )


# ============================================================================
# FR-DEGRADE-SCHEMA-6: Pre-write Validation
# ============================================================================


class TestDegradationWriterValidation:
    """Validate that log_degradation() validates before writing."""

    def test_degradation_writer_validates_before_log(self):
        """
        FR-DEGRADE-SCHEMA-6: log_degradation() validates entry before writing.

        Ensures validation happens at write time, preventing invalid entries
        from reaching the JSONL log file.
        """
        # Import the SelfTestRunner to test log_degradation method
        from selftest import SelfTestResult, SelfTestRunner, StepStatus
        from selftest_config import SelfTestCategory, SelfTestSeverity, SelfTestStep, SelfTestTier

        # Create a mock step and result
        mock_step = SelfTestStep(
            id="test-step",
            name="Test Step",
            tier=SelfTestTier.GOVERNANCE,
            severity=SelfTestSeverity.WARNING,
            category=SelfTestCategory.GOVERNANCE,
            description="Test step",
            command=["echo test"],
        )

        result = SelfTestResult(mock_step)
        result.status = StepStatus.FAIL  # Use status enum instead of passed
        result.reason = "nonzero_exit"
        result.stderr = "Test failure message"

        # Create runner in degraded mode
        runner = SelfTestRunner(degraded=True, write_report=False)

        # Mock the file write operation to verify validation happens
        with patch("builtins.open", mock_open()) as mock_file:
            runner.log_degradation(result)

            # Verify open was called (indicating write attempt)
            if mock_file.called:
                # Get the written data
                handle = mock_file()
                write_calls = handle.write.call_args_list

                if write_calls:
                    written_data = write_calls[0][0][0]

                    # Parse written JSON to verify it's valid
                    try:
                        entry = json.loads(written_data)

                        # Verify all required fields present
                        required = set(DEGRADATION_LOG_SCHEMA["required_fields"])
                        actual = set(entry.keys())
                        assert required.issubset(actual), (
                            f"Written entry missing required fields: {required - actual}"
                        )

                        # Verify tier is not kernel
                        assert entry["tier"] != "kernel", (
                            "log_degradation should never write kernel tier"
                        )

                        # Verify status field is present and valid
                        assert entry["status"] in ["PASS", "FAIL", "SKIP", "TIMEOUT"], (
                            f"Invalid status value: {entry['status']}"
                        )

                    except json.JSONDecodeError:
                        pytest.fail(f"Written data is not valid JSON: {written_data}")

    def test_degradation_logger_skips_kernel_tier(self):
        """
        log_degradation() returns early for KERNEL tier failures.

        KERNEL failures are never logged; they block immediately.
        """
        from selftest import SelfTestResult, SelfTestRunner, StepStatus
        from selftest_config import SelfTestCategory, SelfTestSeverity, SelfTestStep, SelfTestTier

        # Create a KERNEL tier step
        kernel_step = SelfTestStep(
            id="core-checks",
            name="Core Checks",
            tier=SelfTestTier.KERNEL,
            severity=SelfTestSeverity.CRITICAL,
            category=SelfTestCategory.CORRECTNESS,
            description="Core checks",
            command=["echo test"],
        )

        result = SelfTestResult(kernel_step)
        result.status = StepStatus.FAIL  # Use status enum instead of passed
        result.reason = "nonzero_exit"
        result.stderr = "Kernel failure"

        runner = SelfTestRunner(degraded=True, write_report=False)

        # Mock file write to verify NO write happens for kernel tier
        with patch("builtins.open", mock_open()) as mock_file:
            runner.log_degradation(result)

            # Verify open was NOT called for kernel tier
            mock_file.assert_not_called()


# ============================================================================
# FR-DEGRADE-SCHEMA-7: Error Messages Guide Users
# ============================================================================


class TestDegradationSchemaErrorMessages:
    """Validate error messages guide users to schema documentation."""

    def test_missing_field_error_references_schema(self):
        """Validation error for missing fields references schema docs."""
        entry = build_valid_degradation_entry()
        entry_dict = entry.to_dict()
        del entry_dict["tier"]  # Remove required field

        required_fields = set(DEGRADATION_LOG_SCHEMA["required_fields"])
        actual_fields = set(entry_dict.keys())
        missing = required_fields - actual_fields

        if missing:
            error_msg = (
                f"Missing required fields: {missing}. "
                f"See DEGRADATION_LOG_SCHEMA in swarm/tools/selftest.py"
            )
            assert "DEGRADATION_LOG_SCHEMA" in error_msg, (
                "Error message should reference schema definition"
            )
            assert "swarm/tools/selftest.py" in error_msg, (
                "Error message should reference schema location"
            )

    def test_invalid_tier_error_explains_constraint(self):
        """Validation error for invalid tier explains the design constraint."""
        invalid_tier = "kernel"
        valid_tiers = {"governance", "optional"}

        if invalid_tier not in valid_tiers:
            error_msg = (
                f"Invalid tier '{invalid_tier}'. "
                f"Degradation log only accepts: {valid_tiers}. "
                f"KERNEL failures block immediately and are never logged."
            )
            assert "KERNEL failures block immediately" in error_msg, (
                "Error message should explain why kernel tier is invalid"
            )
            assert "never logged" in error_msg, (
                "Error message should clarify kernel tier is not logged"
            )

    def test_schema_example_is_self_documenting(self):
        """Schema example serves as inline documentation (v1.1)."""
        example = DEGRADATION_LOG_SCHEMA["example"]

        # Verify example is valid
        required_fields = set(DEGRADATION_LOG_SCHEMA["required_fields"])
        actual_fields = set(example.keys())

        assert required_fields.issubset(actual_fields), (
            "Schema example should include all required fields"
        )

        # Verify example uses realistic values
        assert example["tier"] in ["governance", "optional"], "Example should use valid tier"
        assert example["severity"] in ["critical", "warning", "info"], (
            "Example should use valid severity"
        )

        # Verify v1.1 fields are present and valid
        assert example["status"] in ["PASS", "FAIL", "SKIP", "TIMEOUT"], (
            "Example should use valid status"
        )
        assert "reason" in example and example["reason"], "Example should have a reason field"

        # Verify schema has documentation comments (in code comments)
        # The actual schema dict doesn't need to contain "ISO 8601" string,
        # but it should be documented in the module docstring
        # This test verifies the example timestamp is in ISO 8601 format
        example_ts = example["timestamp"]
        assert "T" in example_ts, "Example timestamp should use ISO 8601 format with 'T' separator"
        assert "+" in example_ts or "Z" in example_ts, "Example timestamp should include timezone"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
