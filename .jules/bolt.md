
## 2024-05-20 - Faster Directory Size Calculation
**Learning:** Using `pathlib.Path.rglob("*")` inside `get_dir_size` is slow for directories with many files because it creates generator overhead and performs redundant internal `stat` checks.
**Action:** Replace `rglob` with recursive `os.scandir` to avoid generator overhead and reduce redundant `stat` calls.
