## 2026-01-21 - Empty State Actions
**Learning:** Empty states are prime real estate for "micro-onboarding". Adding a copyable command to the empty state transforms a dead end ("No run selected") into an actionable starting point ("Run this command to start").
**Action:** Always look for static commands/paths in UI text and wrap them with a one-click copy action.

## 2026-05-23 - Dynamic Status Announcements
**Learning:** Dynamic status indicators (like "Running", "Stopped") are often implemented as simple text changes, which are invisible to screen readers without `aria-live`.
**Action:** Always wrap dynamic status text in an element with `aria-live="polite"` (or "assertive" for critical alerts).
