## 2025-05-21 - Parallelize Initial Data Loading
**Learning:** The Flow Studio initialization sequence performed `loadRuns()` and `loadFlows()` sequentially, creating a waterfall in the critical path. Parallelizing these using `Promise.allSettled` (with careful handling of dependent state like `setActiveFlow`) reduces the time-to-interactive by overlapping the network latency.
**Action:** Always look for sequential `await` calls in initialization logic that don't have data dependencies on each other. Use `Promise.all` or `Promise.allSettled` to execute them concurrently.
