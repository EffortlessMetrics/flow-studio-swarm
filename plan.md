1. **Update `10-header.html`**
   - Add a context-specific `aria-label="Copy make dev-check command to clipboard"` to the `#copy-dev-check-btn` element.
2. **Update `50-inspector.html`**
   - Add `aria-label="Copy gen_flows command to clipboard"` and `aria-label="Copy validate-swarm command to clipboard"` to the generic `.copy-btn` elements to improve accessibility.
3. **Rebuild the frontend**
   - Run `make gen-index-html` to propagate changes to `index.html`.
4. **Update Palette Journal**
   - Add an entry to `.Jules/palette.md` noting the importance of context-specific `aria-label`s for repeated generic utility buttons.
5. **Verify changes**
   - Run `uv run pytest tests/test_flow_studio_a11y.py` to ensure accessibility tests pass.
6. **Pre-commit steps**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
