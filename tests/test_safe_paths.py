import pytest
from swarm.runtime.safe_paths import validate_path_component


def test_validate_path_component_valid():
    """Test that valid path components are accepted."""
    valid_inputs = [
        "run_123",
        "flow-key",
        "step.id",
        "run_123-abc",
        "123",
        "a",
    ]
    for input_str in valid_inputs:
        assert validate_path_component(input_str) == input_str

def test_validate_path_component_invalid():
    """Test that invalid path components raise ValueError."""
    # These should raise "Invalid path component..."
    invalid_chars_inputs = [
        "..",
        "../parent",
        "dir/file",
        "/absolute/path",
        "run\\id",
        "run~1",
        " run",
        "run ",
        ".",
    ]
    for input_str in invalid_chars_inputs:
        with pytest.raises(ValueError, match="Invalid path component"):
            validate_path_component(input_str)

    # This raises "Path component cannot be empty"
    with pytest.raises(ValueError, match="Path component cannot be empty"):
        validate_path_component("")

def test_validate_path_component_types():
    """Test that non-string inputs raise ValueError or TypeError."""
    with pytest.raises((ValueError, TypeError)):
        validate_path_component(None)
    with pytest.raises((ValueError, TypeError)):
        validate_path_component(123)
