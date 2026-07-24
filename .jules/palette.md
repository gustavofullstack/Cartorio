## 2026-06-30 - Focus visible outlines
**Learning:** The dashboard components use `outline: none;` on `:focus-visible` states, which breaks keyboard navigation. The `operations-dashboard` and `user-review-dashboard` are generated from python templates where this CSS is located.
**Action:** When updating dashboard styles, make sure to separate `:hover` and `:focus-visible` pseudo-classes to provide an explicit visual focus indicator (like `outline: 2px solid var(--brand);`) for accessibility without interfering with mouse-driven hover states.
