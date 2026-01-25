## 2026-01-21 - Empty State Actions
**Learning:** Empty states are prime real estate for "micro-onboarding". Adding a copyable command to the empty state transforms a dead end ("No run selected") into an actionable starting point ("Run this command to start").
**Action:** Always look for static commands/paths in UI text and wrap them with a one-click copy action.

## 2026-02-18 - Modal ID Copying
**Learning:** Users frequently need to copy identifiers (Run IDs) from details modals to CLI or other tools. These are often rendered as static text.
**Action:** Always pair displayed IDs in modals with a `copy-btn` component to reduce friction in the debug loop.
