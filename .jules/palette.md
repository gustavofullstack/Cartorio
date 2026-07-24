## 2026-07-24 - Accessibility: Focus visible outline improvements
**Learning:** Found accessibility issues in dashboards where `:focus-visible` elements had `outline: none;`, completely obscuring keyboard focus indicators for interactive buttons (like menu buttons, close dialog buttons, copy buttons, etc.).
**Action:** Replaced `outline: none;` with `outline: 2px solid var(--brand);` on these buttons across the codebase to ensure keyboard accessibility, keeping within the Palette constraint of avoiding `outline: none;` on `:focus-visible` states.
