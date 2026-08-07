## 2026-06-25 - Combined focus and hover states break keyboard navigation
**Learning:** Combining `:hover` and `:focus-visible` states to apply `outline: none;` on interactive elements hides the focus ring for keyboard users.
**Action:** When overriding default outlines, keep `outline: none;` on the combined rule to avoid focus rings on mouse clicks, but always append a new, distinct rule specifically for `:focus-visible` (e.g. `outline: 2px solid var(--brand);`) to maintain keyboard accessibility.
