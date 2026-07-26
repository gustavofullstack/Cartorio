## 2026-07-26 - Keyboard Accessibility for Interactive Elements
**Learning:** Interactive elements such as `.close`, `.copy-button`, and `.menu button` used `outline: none;` on `:focus-visible` state, which removes the visual focus indicator making keyboard navigation inaccessible.
**Action:** Replaced `outline: none;` with an explicit visual focus indicator (`outline: 2px solid var(--brand);`) for these elements on their `:focus-visible` state across both user-review and operations dashboards to maintain keyboard accessibility.
