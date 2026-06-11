
## 2026-06-11 - Add missing focus-visible styles for keyboard accessibility
**Learning:** Several interactive elements (such as secondary buttons, filter buttons, modal close icons, dropdown buttons, teaching mode toggles, mode toggles, view toggles, and select elements) lacked explicit keyboard focus states in `flow-studio.base.css`, hindering accessibility for keyboard-only users.
**Action:** Always ensure that every custom interactive element explicitly defines a `:focus-visible` pseudo-class (preferably using an outline) to maintain a seamless keyboard navigation experience while avoiding visual clutter on mouse click.
