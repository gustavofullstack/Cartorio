## 2024-09-08 - Dynamic AI Output Accessibility
**Learning:** Dynamically populated AI result containers and code output boxes must include `aria-live="polite"` so screen readers announce the newly generated content when users trigger a calculation or extraction.
**Action:** Always add `aria-live="polite"` to containers that display asynchronous AI results or dynamic breakdowns, like `resultContainer` and `jsonOutput` in `dashboard.html`.
