## 2024-03-24 - [Static UIID Checks]
**Learning:** This repo enforces `data-uiid` presence via static analysis of `index.html` (generated from fragments). Dynamic components (like modal contents) must have static placeholders in the source HTML fragments to pass tests, even if they are replaced by JS at runtime.
**Action:** Always include a hidden placeholder with the correct `data-uiid` for any dynamic component required by `TestFlowStudioUIIDs`.
