## 2025-02-27 - Screen Reader Support for Vanilla JS Dynamic Content
**Learning:** Static HTML dashboards that use vanilla JavaScript `fetch` and `.innerHTML`/`.innerText` to dynamically populate DOM nodes bypass screen readers, leaving visually impaired users unaware of updates (like price extraction results).
**Action:** Always add `role="status"` or `aria-live="polite"` directly to the container elements whose contents change dynamically so that assistive technologies announce the updates automatically.
