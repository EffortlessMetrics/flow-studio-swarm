## 2024-05-20 - Ensure aria-pressed syncs with view/mode toggle states
**Learning:** Found that view toggle buttons ('Author' vs 'Operator', 'Steps/Agents' vs 'Artifacts') did not synchronize their `aria-pressed` state with the visual `active` CSS class.
**Action:** Always verify that state toggle buttons manually synchronize `aria-pressed` alongside CSS class additions, ensuring keyboard and screen reader accessibility.
