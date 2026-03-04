1. **Identify Vulnerability**: Path traversal vulnerabilities exist in `evolution.py` and `wisdom.py` where user-supplied path parameters (`run_id`, `patch_id`, `artifact_name`) are not properly validated before being used to construct file paths.
2. **Add Validation Helper**: Add a helper to catch `ValueError` from `validate_path_component` and raise `HTTPException(400)`.
3. **Apply Validation**: Apply this helper to `run_id`, `patch_id`, and `artifact_name` in all relevant endpoints in `evolution.py` and `wisdom.py`.
4. **Handle Composite IDs**: Ensure `patch_id` in `ApplyEvolutionRequest` is properly split and both parts are validated separately.
5. **Update Tests**: Add tests in `tests/test_security_path_traversal.py` to cover these endpoints as instructed.
6. **Pre-commit Steps**: Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
7. **Submit**: Submit the PR using Sentinel persona format.
