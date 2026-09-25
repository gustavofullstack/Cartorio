## 2023-10-25 - Dynamic DOM Announcements in Vanilla JS
**Learning:** The static HTML dashboards rely heavily on vanilla JavaScript for dynamic DOM updates (e.g., `#resultContainer`, `#jsonOutput`, `#items`). Without React/framework lifecycle hooks, these injected results are completely invisible to screen readers unless explicitly marked.
**Action:** Always add `role="status"` or `aria-live="polite"` to target containers whenever creating dashboards that use `fetch` and `.innerHTML` updates.
