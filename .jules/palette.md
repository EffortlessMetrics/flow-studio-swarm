## 2024-05-22 - [Accessible Copy Button Pattern]
**Learning:** Copy buttons require both static accessible names (`aria-label`) and dynamic feedback (`aria-live` or updated label) for screen readers. Simply changing text content is often insufficient for non-visual users to know the action succeeded.
**Action:** Use the `setupCopyButton` utility which handles `aria-label` updates and restoration automatically for all future copy interactions.
