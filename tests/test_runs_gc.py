from pathlib import Path
from swarm.tools.runs_gc import get_dir_size

def test_get_dir_size(tmp_path):
    (tmp_path / "file1.txt").write_text("hello")
    (tmp_path / "file2.txt").write_text("world!")
    d = tmp_path / "dir1"
    d.mkdir()
    (d / "file3.txt").write_text("12345")

    assert get_dir_size(tmp_path) == 5 + 6 + 5
