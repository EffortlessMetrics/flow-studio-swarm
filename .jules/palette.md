## 2024-05-22 - Standardizing Loading States
**Learning:** The application had inconsistent loading states: some used a spinner (`fs-loading-spinner`), while others used plain text ("Loading..."). The `renderLoading` helper was underutilized and returned plain text.
**Action:** Updated `renderLoading` to use the standardized `.fs-loading` component with a spinner. Refactored `details.ts` to use this helper, ensuring consistent visual feedback across the application. Future loading states should use `renderLoading()`.
