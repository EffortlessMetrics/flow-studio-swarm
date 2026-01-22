## 2026-01-22 - Skip-to-Content Link (PR #215 → #233)

**Original PR**: #215 by Jules
**Replacement PR**: #233 (maintainer takeover)

### What We Built
An accessible skip-to-content link that allows keyboard users to bypass the header and sidebar navigation and jump directly to the main graph content.

### WCAG Compliance
- Success Criterion 2.4.1 - Bypass Blocks (Level A)
- Users can skip repetitive content blocks using a single keyboard action (Tab)

### Implementation Pattern
```css
.skip-to-content {
  position: absolute;
  top: -9999px;           /* Hidden off-screen by default */
  left: 50%;
  transform: translateX(-50%);
  z-index: 10000;         /* Above all other content */
}

.skip-to-content:focus {
  top: 0;                 /* Slide into view when focused */
}
```

### Key Learning: Source File Workflow
**Don't manually patch generated files.** The correct pattern for Flow Studio UI changes:

1. Edit source files (`fragments/*.html`, `css/*.css`, `js/*.js`)
2. Regenerate `index.html` via `make gen-index-html` or `uv run python swarm/tools/gen_index_html.py`
3. Commit the source changes AND the regenerated output

This ensures:
- The build process stays deterministic
- Changes are traceable to their sources
- Future regenerations don't lose the changes
