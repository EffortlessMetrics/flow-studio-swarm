
## 2026-06-22 - Improve Button Accessibility for Screen Readers
**Learning:** When icon-only buttons use literal text characters (like '?' or '×') and also have an aria-label, screen readers might redundantly announce both the label and the character. Additionally, static aria-labels on buttons whose text dynamically changes (like a Copy button that turns to Copied) override the dynamic text, hiding state changes from assistive tech.
**Action:** Always wrap literal text characters in `<span aria-hidden="true">`, inside icon-only buttons that have aria-labels. Remove static aria-labels from buttons with descriptive visible text, especially if that text updates dynamically.
