## YYYY-MM-DD - [Wisdom and Evolution Path Traversal]
**Vulnerability:** The API endpoints under `wisdom` and `evolution` allowed path traversal attacks through unvalidated user inputs (like `run_id`, `artifact_name`, `patch_id`).
**Learning:** FastApi path matching can let through certain characters (like encoded backslashes `%5c`) which OS file APIs interpret as directory separators leading to file reading from unauthorized locations or writing data into them.
**Prevention:** Using a standard `_validate_path_param` implementation (which wraps `validate_path_component`) for all user-supplied paths ensures inputs adhere strictly to a safe format without any slash characters.
