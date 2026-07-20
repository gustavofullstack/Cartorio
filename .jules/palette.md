## 2026-07-28 - Avoid outline:none for focus-visible
**Learning:** Found multiple instances of `outline: none;` on `:focus-visible` pseudo-classes across the operations and user review dashboards. This breaks keyboard accessibility by removing the browser's default visual focus indicator, making it impossible for keyboard users to track their location on the page.
**Action:** Always provide an explicit visual focus indicator (e.g., `outline: 2px solid var(--brand)`) when styling `:focus-visible` states to ensure the application remains accessible to keyboard users.
