## 2025-05-24 - Frontend Debouncing
**Learning:** Flow Studio UI used a 200ms debounce for search, which is aggressive for API-backed searches.
**Action:** Increased to 300ms. Also noted that Run Control UI has complex state management that gets recompiled on build, so care must be taken to only commit relevant artifacts.
