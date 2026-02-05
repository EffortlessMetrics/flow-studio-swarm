## 2024-05-22 - Accessibility in Flow Studio Fragments
**Learning:** Flow Studio UI is assembled from HTML fragments. To improve accessibility (like adding ARIA labels), we must edit the source fragments (`swarm/tools/flow_studio_ui/fragments/*.html`) and then regenerate the index file (`make gen-index-html`). Modifying `index.html` directly will be overwritten.
**Action:** Always check for source fragments when dealing with generated files. Use `aria-label` for repetitive buttons (like "Copy") to provide context to screen readers.
