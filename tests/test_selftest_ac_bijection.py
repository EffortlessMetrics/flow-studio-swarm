"""
Test AC bijection between Gherkin tags, Matrix docs, and config ac_ids.

This test module validates that AC identifiers are consistently defined across:
1. Gherkin feature file (@AC-SELFTEST-* tags)
2. SELFTEST_AC_MATRIX.md (### AC-SELFTEST-* headers)
3. selftest_config.py (ac_ids lists in SELFTEST_STEPS)

Purpose: Prevent drift between test scenarios, documentation, and implementation.
"""

import re
from pathlib import Path

import pytest

# File paths
GHERKIN_FILE = Path("features/selftest.feature")
MATRIX_FILE = Path("docs/SELFTEST_AC_MATRIX.md")
CONFIG_FILE = Path("swarm/tools/selftest_config.py")


def parse_gherkin_acs() -> set[str]:
    """
    Extract AC tags from Gherkin feature file.

    Looks for @AC-SELFTEST-* tags in scenario tags.
    Example: @AC-SELFTEST-KERNEL-CHECKS

    Returns:
        Set of AC identifiers found in Gherkin file.
    """
    if GHERKIN_FILE.is_symlink():
        pytest.skip(f"Skipping symlink: {GHERKIN_FILE}")

    if not GHERKIN_FILE.exists():
        pytest.skip(f"Gherkin file not found: {GHERKIN_FILE}")

    content = GHERKIN_FILE.read_text(encoding="utf-8")

    # Match @AC-SELFTEST-* tags
    pattern = r"@(AC-SELFTEST-[A-Z-]+)"
    matches = re.findall(pattern, content)

    return set(matches)


def parse_matrix_acs() -> set[str]:
    """
    Extract AC identifiers from SELFTEST_AC_MATRIX.md.

    Looks for ### AC-SELFTEST-* markdown headers.
    Example: ### AC-SELFTEST-KERNEL-CHECKS

    Returns:
        Set of AC identifiers found in Matrix documentation.
    """
    if MATRIX_FILE.is_symlink():
        pytest.skip(f"Skipping symlink: {MATRIX_FILE}")

    if not MATRIX_FILE.exists():
        pytest.skip(f"Matrix file not found: {MATRIX_FILE}")

    content = MATRIX_FILE.read_text(encoding="utf-8")

    # Match ### AC-SELFTEST-* headers
    pattern = r"###\s+(AC-SELFTEST-[A-Z-]+)"
    matches = re.findall(pattern, content)

    return set(matches)


def parse_config_acs() -> set[str]:
    """
    Extract AC identifiers from selftest_config.py.

    Looks for ac_ids lists in SELFTEST_STEPS dictionary.
    Example: "ac_ids": ["AC-SELFTEST-KERNEL-CHECKS"]

    Returns:
        Set of AC identifiers found in config file.
    """
    if CONFIG_FILE.is_symlink():
        pytest.skip(f"Skipping symlink: {CONFIG_FILE}")

    if not CONFIG_FILE.exists():
        pytest.skip(f"Config file not found: {CONFIG_FILE}")

    content = CONFIG_FILE.read_text(encoding="utf-8")

    # Match AC-SELFTEST-* identifiers in ac_ids lists
    # Handles both single-line and multi-line list formats
    pattern = r'"(AC-SELFTEST-[A-Z-]+)"'
    matches = re.findall(pattern, content)

    return set(matches)


def test_ac_gherkin_tags_match_matrix():
    """
    Verify all Gherkin @AC-SELFTEST-* tags are documented in Matrix.

    Ensures every AC referenced in test scenarios has corresponding
    documentation in SELFTEST_AC_MATRIX.md.
    """
    gherkin_acs = parse_gherkin_acs()
    matrix_acs = parse_matrix_acs()

    missing_in_matrix = gherkin_acs - matrix_acs

    assert not missing_in_matrix, (
        f"AC tags found in Gherkin but missing in Matrix documentation: "
        f"{sorted(missing_in_matrix)}\n"
        f"Add these ACs as '### <AC-ID>' headers in {MATRIX_FILE}"
    )


def test_ac_matrix_matches_config():
    """
    Verify all Matrix AC headers appear in config ac_ids.

    Ensures every documented AC is actually tracked in the selftest
    configuration for enforcement.
    """
    matrix_acs = parse_matrix_acs()
    config_acs = parse_config_acs()

    missing_in_config = matrix_acs - config_acs

    assert not missing_in_config, (
        f"AC identifiers found in Matrix but missing in Config ac_ids: "
        f"{sorted(missing_in_config)}\n"
        f"Add these ACs to appropriate step 'ac_ids' lists in {CONFIG_FILE}"
    )


def test_ac_config_has_no_orphans():
    """
    Verify all config ac_ids are documented in Matrix (no orphans).

    Ensures the config doesn't reference AC identifiers that aren't
    documented. Orphaned ACs indicate missing documentation or typos.
    """
    config_acs = parse_config_acs()
    matrix_acs = parse_matrix_acs()

    orphaned_in_config = config_acs - matrix_acs

    assert not orphaned_in_config, (
        f"AC identifiers found in Config but missing in Matrix documentation: "
        f"{sorted(orphaned_in_config)}\n"
        f"Add documentation for these ACs in {MATRIX_FILE} or remove from {CONFIG_FILE}"
    )


def test_bidirectional_consistency():
    """
    Verify complete bidirectional consistency across all three sources.

    This meta-test ensures:
    1. Gherkin → Matrix (covered by test_ac_gherkin_tags_match_matrix)
    2. Matrix → Config (covered by test_ac_matrix_matches_config)
    3. Config → Matrix (covered by test_ac_config_has_no_orphans)

    If this test passes, the AC namespace is fully synchronized.
    """
    gherkin_acs = parse_gherkin_acs()
    matrix_acs = parse_matrix_acs()
    config_acs = parse_config_acs()

    # Check if Matrix is the complete superset
    missing_from_matrix = (gherkin_acs | config_acs) - matrix_acs

    assert not missing_from_matrix, (
        f"Matrix should be complete documentation of all ACs.\n"
        f"ACs referenced elsewhere but missing from Matrix: {sorted(missing_from_matrix)}"
    )

    # Check if Config covers all documented ACs
    undocumented_in_config = matrix_acs - config_acs

    assert not undocumented_in_config, (
        f"Config should track all documented ACs.\n"
        f"ACs documented in Matrix but not tracked in Config: {sorted(undocumented_in_config)}"
    )


if __name__ == "__main__":
    # Allow running directly for quick validation
    pytest.main([__file__, "-v"])
