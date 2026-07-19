## 2026-07-19 - Removed outline:none for focus visible to ensure keyboard accessibility
**Learning:** Found the outline: none CSS rule being used for :focus-visible selectors on interactive elements like buttons and modals.
**Action:** Always provide an explicit visual focus indicator (e.g. outline: 2px solid var(--brand)) instead of outline: none.
