## 2026-01-22 - Canvas Copy Button A11y (PR #208 → #234)

**Original PR**: #208 by Jules
**Replacement PR**: #234 (maintainer takeover)

### What We Fixed
Added `aria-label="Copy demo command to clipboard"` to the canvas empty state copy button so screen readers announce the button's purpose.

### Why Not Jules' Approach?
Jules #208 proposed:
1. Replace inline onclick with `createCopyButton` utility
2. Use JavaScript runtime injection (empty div + appendChild)
3. Bundle unrelated run_control.ts changes

Problems with this:
- **Complexity**: Runtime injection for a static button is overkill
- **Consistency**: Inline onclick is the pattern used elsewhere (PR #232)
- **Scope creep**: Bundled run_control changes were unrelated to accessibility

### The Simpler Fix
Just add `aria-label` to the existing button. One attribute change, same behavioral result.

### Key Learning
When Jules bundles unrelated changes:
1. Identify the core improvement (aria-label)
2. Apply it with minimal scope
3. Let drift fixes happen naturally through regeneration
4. Don't adopt more complex architecture unless it's justified
