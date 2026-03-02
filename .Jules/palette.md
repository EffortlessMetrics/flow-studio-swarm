## $(date +%Y-%m-%d) - Context-Specific ARIA Labels for Utility Buttons
**Learning:** Generic utility buttons like "Copy" lack surrounding context when read by a screen reader out of sequence. While visual users can associate a "Copy" button with the adjacent code block, screen reader users may just hear "Copy, button" without knowing what is being copied.
**Action:** Always add explicit, context-specific `aria-label` attributes to generic utility buttons (e.g., `aria-label="Copy dev-check command to clipboard"`) rather than relying purely on visible text or `title` attributes.
