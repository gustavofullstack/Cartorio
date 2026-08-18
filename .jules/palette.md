## 2026-08-17 - Added focus-visible and aria-label to btn-action
**Learning:** Found a primary call-to-action button missing screen reader context and keyboard focus styling in static HTML dashboard.
**Action:** When adding accessibility to interactive elements, always ensure `:focus-visible` is explicitly styled alongside `:hover`, and use `aria-label` to describe buttons that contain emojis or icon-heavy text.
