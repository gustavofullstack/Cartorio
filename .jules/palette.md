## 2025-03-26 - Add ARIA live regions for dynamic results
**Learning:** When results are calculated and displayed dynamically without a page reload, screen reader users miss the update unless the container is marked as a live region.
**Action:** Always add `aria-live="polite"` and `aria-atomic="true"` to containers whose content is updated asynchronously after user interaction (like calculating results or fetching prices).
