"""
Test suite for bdd_validator.py.

Tests the BDDValidator class which validates Gherkin .feature files
for correct structure (Feature, Scenario, steps).
"""

# Import the module under test
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "swarm" / "tools"))
from bdd_validator import BDDValidator

# ============================================================================
# Happy Path Tests
# ============================================================================


def test_valid_feature_file(tmp_path):
    """
    Valid feature file passes validation.

    Given: A .feature file with Feature, Scenario, and steps
    When: I run the validator
    Then: Validation passes with no errors
    """
    features_dir = tmp_path / "features"
    features_dir.mkdir()

    feature_file = features_dir / "health_check.feature"
    feature_file.write_text("""Feature: Health check endpoint
  As an operator
  I want to verify the system is running
  So that I can monitor its status

  Scenario: Basic health check returns OK
    Given the server is running
    When I request GET /health
    Then the response status should be 200
    And the response body should contain "ok"
""")

    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is True
    assert errors == []


def test_feature_with_multiple_scenarios(tmp_path):
    """
    Feature file with multiple scenarios passes validation.

    Given: A .feature file with Feature and multiple Scenarios
    When: I run the validator
    Then: Validation passes for all scenarios
    """
    features_dir = tmp_path / "features"
    features_dir.mkdir()

    feature_file = features_dir / "auth.feature"
    feature_file.write_text("""Feature: Authentication
  Users can log in and out

  Scenario: Successful login
    Given a valid user exists
    When the user submits correct credentials
    Then the user should be logged in

  Scenario: Failed login
    Given a valid user exists
    When the user submits incorrect password
    Then the login should be rejected
""")

    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is True
    assert errors == []


def test_no_features_directory(tmp_path):
    """
    Missing features directory is acceptable.

    Given: No features directory exists
    When: I run the validator
    Then: Validation passes (no features to validate)
    """
    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is True
    assert errors == []


def test_empty_features_directory(tmp_path):
    """
    Empty features directory is acceptable.

    Given: An empty features directory exists
    When: I run the validator
    Then: Validation passes (no feature files)
    """
    features_dir = tmp_path / "features"
    features_dir.mkdir()

    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is True
    assert errors == []


# ============================================================================
# Error Path Tests
# ============================================================================


def test_missing_feature_keyword(tmp_path):
    """
    Feature file without 'Feature:' keyword fails validation.

    Given: A .feature file without 'Feature:' keyword
    When: I run the validator
    Then: Validation fails with missing Feature error
    """
    features_dir = tmp_path / "features"
    features_dir.mkdir()

    feature_file = features_dir / "broken.feature"
    feature_file.write_text("""# This is just a comment
Scenario: Missing feature keyword
  Given something
  When something else
  Then result
""")

    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert len(errors) == 1
    assert "broken.feature" in errors[0]
    assert "Feature:" in errors[0]


def test_missing_scenario_keyword(tmp_path):
    """
    Feature file without any 'Scenario:' keyword fails validation.

    Given: A .feature file with Feature but no Scenario
    When: I run the validator
    Then: Validation fails with missing Scenario error
    """
    features_dir = tmp_path / "features"
    features_dir.mkdir()

    feature_file = features_dir / "noscenario.feature"
    feature_file.write_text("""Feature: Feature without scenarios
  This feature has no scenarios defined.
""")

    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert len(errors) == 1
    assert "noscenario.feature" in errors[0]
    assert "Scenario:" in errors[0]


def test_scenario_without_steps(tmp_path):
    """
    Scenario without any Given/When/Then steps fails validation.

    Given: A .feature file with empty Scenario
    When: I run the validator
    Then: Validation fails with 'no steps' error
    """
    features_dir = tmp_path / "features"
    features_dir.mkdir()

    feature_file = features_dir / "nosteps.feature"
    feature_file.write_text("""Feature: Feature with empty scenario

  Scenario: Empty scenario
    # No steps here

  Scenario: Another empty one
""")

    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    # Both scenarios should be reported as having no steps
    assert any("Empty scenario" in e and "no steps" in e for e in errors)


def test_multiple_files_with_mixed_validity(tmp_path):
    """
    Validator reports errors for invalid files while passing valid ones.

    Given: Multiple .feature files, some valid, some invalid
    When: I run the validator
    Then: Only invalid files are reported
    """
    features_dir = tmp_path / "features"
    features_dir.mkdir()

    # Valid file
    ok_file = features_dir / "ok.feature"
    ok_file.write_text("""Feature: Valid feature
  Scenario: Works fine
    Given everything is set up
    When I run the test
    Then it passes
""")

    # Invalid file - no scenarios
    broken_file = features_dir / "broken.feature"
    broken_file.write_text("""Feature: Invalid feature
  No scenarios here.
""")

    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert len(errors) == 1
    assert "broken.feature" in errors[0]
    assert "ok.feature" not in errors[0]


def test_nested_feature_files(tmp_path):
    """
    Validator finds feature files in subdirectories.

    Given: Feature files in nested subdirectories
    When: I run the validator
    Then: All feature files are validated
    """
    features_dir = tmp_path / "features"
    (features_dir / "api").mkdir(parents=True)
    (features_dir / "ui").mkdir(parents=True)

    # Valid file in api subdirectory
    api_file = features_dir / "api" / "health.feature"
    api_file.write_text("""Feature: API Health
  Scenario: Health endpoint
    Given the API is running
    When I call /health
    Then I get 200
""")

    # Invalid file in ui subdirectory (no scenarios)
    ui_file = features_dir / "ui" / "broken.feature"
    ui_file.write_text("""Feature: UI tests
  No scenarios defined.
""")

    validator = BDDValidator(tmp_path)
    is_valid, errors = validator.validate()

    assert is_valid is False
    assert len(errors) == 1
    assert "broken.feature" in errors[0]
