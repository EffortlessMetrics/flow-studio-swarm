1. **Fix XXE Vulnerability in `swarm/runtime/test_parser.py`**
   - Change `import xml.etree.ElementTree as ET` to `import defusedxml.ElementTree as ET`. This resolves the XML External Entity (XXE) vulnerability which is critical because it parses XML from tests output which might be untrusted.
2. **Update dependencies**
   - Ensure `defusedxml` is correctly added to `pyproject.toml` and lock file via `uv add defusedxml`.
3. **Verify the change**
   - Check using `git diff`.
   - Run tests `uv run pytest tests/test_test_parser_xml.py` (which we created) to make sure XML parsing works correctly.
   - Delete `tests/test_test_parser_xml.py`.
4. **Update Sentinel Journal**
   - Create or append to `.jules/sentinel.md` noting the finding, learning, and prevention of XXE using `defusedxml`.
5. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**
   - Run `pre_commit_instructions` tool and complete all required pre-commit tasks (lint, format, test).
6. **Submit PR**
   - Submit the PR with the Sentinel persona format as required.
