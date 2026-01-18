## 2025-05-27 - Path Traversal Risks in Pathlib Concatenation
**Vulnerability:** Widespread use of `Path(base) / user_input` allowed path traversal because `pathlib` doesn't automatically sanitize `..` components unless `.resolve()` is called on the result, and even then, logical validation is needed before access.
**Learning:** `pathlib`'s `/` operator is convenient but dangerous with untrusted input. It does not enforce that the result is a child of the left operand.
**Prevention:** Use `validate_path_component` (now in `swarm.runtime.safe_paths`) to strictly validate ID-like inputs before using them in path construction.
