## 2026-07-21 - Add keyboard focus visible states
**Learning:** Both the user review and operations dashboards were entirely missing visual indicators for keyboard focus (`outline: none` was actively disabling it on menus, close buttons, and copy buttons).
**Action:** Replaced `outline: none` with `:focus-visible { outline: 2px solid var(--brand); outline-offset: -2px; }` across all interactive elements, restoring full keyboard navigation accessibility while keeping mouse clicks clean.
