import pytest
from pathlib import Path
import os
from swarm.runtime.safe_paths import safe_join, validate_filename

def test_safe_join_valid(tmp_path):
    base = tmp_path
    child = safe_join(base, "child")
    assert child == base / "child"

    grandchild = safe_join(base, "child/grandchild")
    assert grandchild == base / "child" / "grandchild"

def test_safe_join_traversal(tmp_path):
    base = tmp_path

    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_join(base, "..")

    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_join(base, "child", "..", "..")

    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_join(base, "../secret")

def test_safe_join_absolute(tmp_path):
    base = tmp_path
    # Should resolve to child in base, treating absolute path as relative
    res = safe_join(base, "/etc/passwd")

    # On Windows, /etc/passwd might be interpreted differently, but safe_join strips leading separators
    # So it should be base / "etc" / "passwd"
    expected = base / "etc" / "passwd"

    assert res == expected
    assert res.is_relative_to(base)

def test_validate_filename():
    assert validate_filename("valid.txt") == "valid.txt"
    assert validate_filename("valid-file_name.123") == "valid-file_name.123"

    with pytest.raises(ValueError, match="Invalid filename"):
        validate_filename("invalid/file.txt")

    with pytest.raises(ValueError, match="Invalid filename"):
        validate_filename("/root")

    if os.altsep:
        with pytest.raises(ValueError, match="Invalid filename"):
            validate_filename(f"invalid{os.altsep}file.txt")
