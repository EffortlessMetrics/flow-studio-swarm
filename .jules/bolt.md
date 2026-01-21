## 2025-01-20 - Run Discovery Performance
**Learning:** `pathlib.Path.iterdir()` combined with `Path.exists()` for each entry is significantly slower than `os.scandir()` for large directories, especially when just checking for file existence.
**Action:** Use `os.scandir()` for high-frequency directory scanning, especially in hot paths like run discovery.
