## 2024-05-22 - Emoji Icons and Screen Readers
**Learning:** This codebase frequently uses raw emoji characters (e.g., `\u{1F4C2}` 📂) inside `<div>` elements as decorative icons. Screen readers announce these (e.g., "Open file folder"), adding unnecessary noise to empty states and headers.
**Action:** Always wrap decorative emojis in a container (span/div) with `aria-hidden="true"`, or ensure they are paired with a visible label and hidden themselves. When emojis are used as status indicators (like ✅/❌), ensure there is accompanying text or an `aria-label` providing the same information.
