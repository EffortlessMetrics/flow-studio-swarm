## 2025-05-15 - YAML Loading Performance
**Learning:** `yaml.safe_load` is pure Python and significantly slower (~12x) than `CSafeLoader` for loading YAML files.
**Action:** Always check for `CSafeLoader` availability and use it when parsing YAML files, especially in hot paths or during startup with many configuration files.
