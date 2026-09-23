## 2025-02-23 - Vanilla JS Dynamic DOM Updates Accessibility
**Learning:** In vanilla JavaScript dashboards that dynamically show output boxes (like AI extraction results) or JSON blocks upon user interaction, screen readers remain completely silent unless the target containers explicitly declare `role="status"` or `aria-live="polite"`. Without this, users who rely on screen readers won't know the extraction action succeeded.
**Action:** Always add explicit ARIA live regions to dynamic result containers in static HTML dashboards.
