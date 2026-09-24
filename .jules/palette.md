## 2024-09-24 - ARIA Live Regions for Vanilla JS Dashboards
**Learning:** When using Vanilla JS to dynamically update DOM elements without a framework, screen readers won't announce the updates automatically.
**Action:** Always add `aria-live="polite"` or `role="status"` to containers that receive dynamic data updates via JavaScript to ensure accessibility.
