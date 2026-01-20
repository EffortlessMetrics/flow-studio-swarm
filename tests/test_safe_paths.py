import pytest
from swarm.runtime.safe_paths import validate_path_component

def test_validate_path_component_valid():
    assert validate_path_component("run-123") == "run-123"
    assert validate_path_component("flow_key") == "flow_key"
    assert validate_path_component("step.1") == "step.1"
    assert validate_path_component("123") == "123"
    assert validate_path_component("a-b_c.d") == "a-b_c.d"

def test_validate_path_component_traversal():
    with pytest.raises(ValueError, match="Traversal sequences"):
        validate_path_component("..")

    with pytest.raises(ValueError, match="Traversal sequences"):
        validate_path_component("../etc")

    with pytest.raises(ValueError, match="Traversal sequences"):
        validate_path_component("a/../b")

    with pytest.raises(ValueError, match="Traversal sequences"):
        validate_path_component("foo..bar")

def test_validate_path_component_invalid_chars():
    with pytest.raises(ValueError, match="Must contain only alphanumeric"):
        validate_path_component("run/123")  # slashes not allowed

    with pytest.raises(ValueError, match="Must contain only alphanumeric"):
        validate_path_component("run\\123") # backslashes not allowed

    with pytest.raises(ValueError, match="Must contain only alphanumeric"):
        validate_path_component("run 123")  # spaces not allowed

    with pytest.raises(ValueError, match="Must contain only alphanumeric"):
        validate_path_component("run$123")

def test_validate_path_component_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_path_component("")

    with pytest.raises(ValueError, match="cannot be empty"):
        validate_path_component(None)  # type: ignore

def test_validate_path_component_types():
    with pytest.raises(ValueError, match="must be a string"):
        validate_path_component(123)  # type: ignore
