"""
Tests for selftest remediation suggestion engine.

Validates:
- Pattern matching against error messages
- Suggestion generation
- JSON output format
- Severity filtering
- Log parsing
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

import yaml

# Add parent directory to path to allow importing swarm
sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.tools.selftest_suggest_remediation import (
    DegradationEntry,
    RemediationPattern,
    RemediationSuggestionEngine,
    parse_degradation_log,
)


@pytest.fixture
def remediation_map_data() -> Dict[str, Any]:
    """Sample remediation map data."""
    return {
        "version": "1.0.0",
        "remediation_patterns": [
            {
                "id": "agent-not-found",
                "error_pattern": "Agent .* not found in registry",
                "severity": "governance",
                "suggested_commands": ["make gen-adapters", "make validate-swarm"],
                "rationale": "Config is out of sync; regeneration fixes it",
            },
            {
                "id": "coverage-below-threshold",
                "error_pattern": r"Coverage.*below.*target|Coverage.*\d+%.*target.*\d+%",
                "severity": "optional",
                "suggested_commands": [
                    "make selftest-coverage-report",
                    "uv run pytest --cov",
                ],
                "rationale": "New code needs test coverage; identify gaps",
            },
            {
                "id": "ac-matrix-stale",
                "error_pattern": "AC matrix.*stale|Acceptance criteria.*not updated",
                "severity": "governance",
                "suggested_commands": [
                    "uv run swarm/tools/check_selftest_ac_freshness.py --update"
                ],
                "rationale": "Spec changed but tests didn't; update tool automates alignment",
            },
        ],
    }


@pytest.fixture
def remediation_map_file(tmp_path: Path, remediation_map_data: Dict[str, Any]) -> Path:
    """Create a temporary remediation map file."""
    map_file = tmp_path / "selftest_remediation_map.yaml"
    with open(map_file, "w") as f:
        yaml.dump(remediation_map_data, f)
    return map_file


@pytest.fixture
def sample_degradation_log(tmp_path: Path) -> Path:
    """Create a sample degradation log with 3 entries (2 matching, 1 not)."""
    log_file = tmp_path / "selftest_degradations.log"
    log_content = """2025-12-01T10:00:00 | agents-governance | FAIL | GOVERNANCE | Agent 'foo-bar' not found in registry
2025-12-01T10:01:00 | ac-coverage | WARN | OPTIONAL | Coverage 94% below target 98%
2025-12-01T10:02:00 | graph-invariants | FAIL | GOVERNANCE | Orphaned node detected in flow graph
"""
    log_file.write_text(log_content)
    return log_file


@pytest.fixture
def sample_degradations() -> List[DegradationEntry]:
    """Sample degradation entries."""
    return [
        DegradationEntry(
            timestamp="2025-12-01T10:00:00",
            step="agents-governance",
            status="FAIL",
            error="Agent 'foo-bar' not found in registry",
            severity="GOVERNANCE",
        ),
        DegradationEntry(
            timestamp="2025-12-01T10:01:00",
            step="ac-coverage",
            status="WARN",
            error="Coverage 94% below target 98%",
            severity="OPTIONAL",
        ),
        DegradationEntry(
            timestamp="2025-12-01T10:02:00",
            step="graph-invariants",
            status="FAIL",
            error="Orphaned node detected in flow graph",
            severity="GOVERNANCE",
        ),
    ]


class TestRemediationPattern:
    """Tests for RemediationPattern class."""

    def test_pattern_matches_exact(self, remediation_map_data: Dict[str, Any]) -> None:
        """Test exact pattern matching."""
        pattern = RemediationPattern(remediation_map_data["remediation_patterns"][0])

        assert pattern.matches("Agent 'foo-bar' not found in registry")
        assert pattern.matches("Agent 'test-agent' not found in registry")
        assert not pattern.matches("Agent foo-bar exists")

    def test_pattern_matches_regex(self, remediation_map_data: Dict[str, Any]) -> None:
        """Test regex pattern matching for coverage."""
        pattern = RemediationPattern(remediation_map_data["remediation_patterns"][1])

        assert pattern.matches("Coverage 94% below target 98%")
        assert pattern.matches("Coverage below target")
        assert pattern.matches("Coverage 85% target 90%")
        assert not pattern.matches("Coverage meets target")

    def test_pattern_case_insensitive(self, remediation_map_data: Dict[str, Any]) -> None:
        """Test case-insensitive matching."""
        pattern = RemediationPattern(remediation_map_data["remediation_patterns"][0])

        assert pattern.matches("AGENT 'FOO' NOT FOUND IN REGISTRY")
        assert pattern.matches("agent 'foo' not found in registry")


class TestRemediationSuggestionEngine:
    """Tests for RemediationSuggestionEngine class."""

    def test_engine_loads_patterns(self, remediation_map_file: Path) -> None:
        """Test engine loads patterns from YAML."""
        engine = RemediationSuggestionEngine(remediation_map_file)

        assert len(engine.patterns) == 3
        assert engine.patterns[0].id == "agent-not-found"
        assert engine.patterns[1].id == "coverage-below-threshold"
        assert engine.patterns[2].id == "ac-matrix-stale"

    def test_engine_missing_map_raises_error(self, tmp_path: Path) -> None:
        """Test engine raises error if map file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            RemediationSuggestionEngine(tmp_path / "nonexistent.yaml")

    def test_match_degradation_finds_pattern(
        self, remediation_map_file: Path, sample_degradations: List[DegradationEntry]
    ) -> None:
        """Test matching degradation to pattern."""
        engine = RemediationSuggestionEngine(remediation_map_file)

        # First degradation matches agent-not-found
        pattern = engine.match_degradation(sample_degradations[0])
        assert pattern is not None
        assert pattern.id == "agent-not-found"

        # Second degradation matches coverage-below-threshold
        pattern = engine.match_degradation(sample_degradations[1])
        assert pattern is not None
        assert pattern.id == "coverage-below-threshold"

        # Third degradation has no match
        pattern = engine.match_degradation(sample_degradations[2])
        assert pattern is None

    def test_generate_suggestions_all(
        self, remediation_map_file: Path, sample_degradations: List[DegradationEntry]
    ) -> None:
        """Test generating suggestions for all degradations."""
        engine = RemediationSuggestionEngine(remediation_map_file)
        result = engine.generate_suggestions(sample_degradations)

        assert result["total_degradations"] == 3
        assert result["actionable_suggestions"] == 2
        assert result["unmatched"] == 1
        assert len(result["suggestions"]) == 2

        # Check first suggestion
        suggestion = result["suggestions"][0]
        assert suggestion["degradation"]["step"] == "agents-governance"
        assert suggestion["remediation"]["id"] == "agent-not-found"
        assert "make gen-adapters" in suggestion["remediation"]["suggested_commands"]

        # Check second suggestion
        suggestion = result["suggestions"][1]
        assert suggestion["degradation"]["step"] == "ac-coverage"
        assert suggestion["remediation"]["id"] == "coverage-below-threshold"

    def test_generate_suggestions_severity_filter(
        self, remediation_map_file: Path, sample_degradations: List[DegradationEntry]
    ) -> None:
        """Test severity filtering."""
        engine = RemediationSuggestionEngine(remediation_map_file)

        # Filter for GOVERNANCE only
        result = engine.generate_suggestions(sample_degradations, severity_filter="governance")
        assert result["actionable_suggestions"] == 1
        assert result["suggestions"][0]["degradation"]["severity"] == "GOVERNANCE"

        # Filter for OPTIONAL only
        result = engine.generate_suggestions(sample_degradations, severity_filter="optional")
        assert result["actionable_suggestions"] == 1
        assert result["suggestions"][0]["degradation"]["severity"] == "OPTIONAL"

        # All (no filter)
        result = engine.generate_suggestions(sample_degradations, severity_filter="all")
        assert result["actionable_suggestions"] == 2


class TestParseDegradationLog:
    """Tests for log parsing."""

    def test_parse_log_basic(self, sample_degradation_log: Path) -> None:
        """Test parsing basic degradation log."""
        entries = parse_degradation_log(sample_degradation_log)

        assert len(entries) == 3
        assert entries[0].step == "agents-governance"
        assert entries[0].status == "FAIL"
        assert entries[0].severity == "GOVERNANCE"
        assert "Agent 'foo-bar' not found in registry" in entries[0].error

        assert entries[1].step == "ac-coverage"
        assert entries[1].status == "WARN"
        assert entries[1].severity == "OPTIONAL"

        assert entries[2].step == "graph-invariants"

    def test_parse_log_empty(self, tmp_path: Path) -> None:
        """Test parsing empty log."""
        log_file = tmp_path / "empty.log"
        log_file.write_text("")

        entries = parse_degradation_log(log_file)
        assert len(entries) == 0

    def test_parse_log_nonexistent(self, tmp_path: Path) -> None:
        """Test parsing nonexistent log."""
        entries = parse_degradation_log(tmp_path / "nonexistent.log")
        assert len(entries) == 0

    def test_parse_log_multiline_error(self, tmp_path: Path) -> None:
        """Test parsing log with multiline error messages."""
        log_file = tmp_path / "multiline.log"
        log_content = """2025-12-01T10:00:00 | agents-governance | FAIL | GOVERNANCE | Agent 'foo-bar' not found in registry
  Full traceback:
  File "/path/to/file.py", line 42
2025-12-01T10:01:00 | ac-coverage | WARN | OPTIONAL | Coverage 94% below target 98%
"""
        log_file.write_text(log_content)

        entries = parse_degradation_log(log_file)
        assert len(entries) == 2

        # First entry should contain continuation lines
        assert "Full traceback:" in entries[0].error
        assert 'File "/path/to/file.py"' in entries[0].error


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_cli_json_output(
        self, tmp_path: Path, remediation_map_file: Path, sample_degradation_log: Path
    ) -> None:
        """Test CLI with JSON output."""
        import sys

        from swarm.tools.selftest_suggest_remediation import main

        # Override sys.argv for CLI testing
        original_argv = sys.argv
        try:
            sys.argv = [
                "selftest_suggest_remediation.py",
                "--degradation-log",
                str(sample_degradation_log),
                "--remediation-map",
                str(remediation_map_file),
                "--json",
            ]

            # Capture stdout
            import io
            from contextlib import redirect_stdout

            captured_output = io.StringIO()
            with redirect_stdout(captured_output):
                exit_code = main()

            assert exit_code == 0

            # Parse JSON output
            output = captured_output.getvalue()
            result = json.loads(output)

            assert result["total_degradations"] == 3
            assert result["actionable_suggestions"] == 2
            assert result["unmatched"] == 1

        finally:
            sys.argv = original_argv

    def test_cli_human_readable_output(
        self, tmp_path: Path, remediation_map_file: Path, sample_degradation_log: Path
    ) -> None:
        """Test CLI with human-readable output."""
        import sys

        from swarm.tools.selftest_suggest_remediation import main

        original_argv = sys.argv
        try:
            sys.argv = [
                "selftest_suggest_remediation.py",
                "--degradation-log",
                str(sample_degradation_log),
                "--remediation-map",
                str(remediation_map_file),
            ]

            import io
            from contextlib import redirect_stdout

            captured_output = io.StringIO()
            with redirect_stdout(captured_output):
                exit_code = main()

            assert exit_code == 0

            output = captured_output.getvalue()
            assert "=== Suggestion Pack ===" in output
            assert "Found 3 degradations; 2 actionable suggestions" in output
            assert "agent-not-found" in output
            assert "make gen-adapters" in output
            assert "2 of 3 degradations have actionable suggestions" in output

        finally:
            sys.argv = original_argv

    def test_real_remediation_map(self) -> None:
        """Test with real remediation map from repo."""
        map_path = Path("swarm/config/selftest_remediation_map.yaml")

        if not map_path.exists():
            pytest.skip("Real remediation map not found")

        engine = RemediationSuggestionEngine(map_path)

        # Verify we have multiple patterns
        assert len(engine.patterns) >= 3

        # Test a few known patterns
        pattern_ids = [p.id for p in engine.patterns]
        assert "agent-not-found" in pattern_ids
        assert "coverage-below-threshold" in pattern_ids
        assert "ac-matrix-stale" in pattern_ids

        # Test matching with real patterns
        test_degradation = DegradationEntry(
            timestamp="2025-12-01T10:00:00",
            step="agents-governance",
            status="FAIL",
            error="Agent 'test-agent' not found in registry",
            severity="GOVERNANCE",
        )

        pattern = engine.match_degradation(test_degradation)
        assert pattern is not None
        assert pattern.id == "agent-not-found"


class TestRobustness:
    """Test edge cases and robustness."""

    def test_malformed_log_line(self, tmp_path: Path) -> None:
        """Test parsing log with malformed lines."""
        log_file = tmp_path / "malformed.log"
        log_content = """2025-12-01T10:00:00 | agents-governance | FAIL | GOVERNANCE | Agent 'foo' not found
This line is malformed
2025-12-01T10:01:00 | ac-coverage | WARN | OPTIONAL | Coverage 94% below target
"""
        log_file.write_text(log_content)

        entries = parse_degradation_log(log_file)
        # Should parse 2 valid entries, ignore malformed line
        assert len(entries) == 2

    def test_empty_suggestions(self, remediation_map_file: Path) -> None:
        """Test when no degradations match any pattern."""
        engine = RemediationSuggestionEngine(remediation_map_file)

        # Create degradations that don't match any pattern
        degradations = [
            DegradationEntry(
                timestamp="2025-12-01T10:00:00",
                step="unknown-step",
                status="FAIL",
                error="Some unknown error",
                severity="GOVERNANCE",
            )
        ]

        result = engine.generate_suggestions(degradations)
        assert result["total_degradations"] == 1
        assert result["actionable_suggestions"] == 0
        assert result["unmatched"] == 1
        assert len(result["suggestions"]) == 0

    def test_pattern_with_special_regex_chars(
        self, tmp_path: Path, remediation_map_data: Dict[str, Any]
    ) -> None:
        """Test patterns containing special regex characters."""
        # Add pattern with special chars
        remediation_map_data["remediation_patterns"].append(
            {
                "id": "yaml-error",
                "error_pattern": r"YAML parse error: \[.*\]",
                "severity": "governance",
                "suggested_commands": ["make validate-swarm"],
                "rationale": "Fix YAML syntax",
            }
        )

        map_file = tmp_path / "map.yaml"
        with open(map_file, "w") as f:
            yaml.dump(remediation_map_data, f)

        engine = RemediationSuggestionEngine(map_file)

        degradation = DegradationEntry(
            timestamp="2025-12-01T10:00:00",
            step="agents-governance",
            status="FAIL",
            error="YAML parse error: [line 42]",
            severity="GOVERNANCE",
        )

        pattern = engine.match_degradation(degradation)
        assert pattern is not None
        assert pattern.id == "yaml-error"
