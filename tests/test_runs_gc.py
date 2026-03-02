import pytest
from pathlib import Path
from datetime import datetime, timezone
import json
from swarm.tools.runs_gc import RunInfo

def test_run_info_lazy_loading(tmp_path):
    run_dir = tmp_path / "test_run"
    run_dir.mkdir()

    # Create a small file
    test_file = run_dir / "file.txt"
    test_file.write_text("hello")

    # Create meta file
    meta_path = run_dir / "meta.json"
    meta_path.write_text(json.dumps({"tags": ["tag1", "tag2"]}))

    run_info = RunInfo(
        run_id="test_run",
        path=run_dir,
        run_type="active",
        mtime=datetime.now(timezone.utc),
        has_meta=True
    )

    # Verify eager properties
    assert run_info.run_id == "test_run"
    assert run_info.run_type == "active"
    assert run_info.has_meta is True

    # Verify lazy properties load correctly
    assert run_info._size_bytes is None
    assert run_info.size_bytes > 0
    assert run_info._size_bytes is not None

    assert run_info._tags is None
    assert run_info._is_corrupt is None

    assert run_info.tags == ["tag1", "tag2"]
    assert run_info.is_corrupt is False
    assert run_info._tags is not None
    assert run_info._is_corrupt is not None

def test_run_info_corrupt_meta(tmp_path):
    run_dir = tmp_path / "corrupt_run"
    run_dir.mkdir()

    # Create corrupt meta file
    meta_path = run_dir / "meta.json"
    meta_path.write_text("{invalid json}")

    run_info = RunInfo(
        run_id="corrupt_run",
        path=run_dir,
        run_type="active",
        mtime=datetime.now(timezone.utc),
        has_meta=True
    )

    assert run_info.is_corrupt is True
    assert run_info.tags == []

def test_run_info_no_meta(tmp_path):
    run_dir = tmp_path / "legacy_run"
    run_dir.mkdir()

    run_info = RunInfo(
        run_id="legacy_run",
        path=run_dir,
        run_type="legacy",
        mtime=datetime.now(timezone.utc),
        has_meta=False
    )

    assert run_info.is_corrupt is False
    assert run_info.tags == []
