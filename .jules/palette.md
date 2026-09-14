## 2026-08-10 - Focus Outline for combined Hover and Focus states
**Learning:** In this codebase, when applying `outline: none;` to combined `:hover, :focus-visible` states to prevent focus rings on mouse clicks, a separate, distinct rule exclusively for `:focus-visible` (e.g., `outline: 2px solid var(--brand);`) must be appended to ensure keyboard navigation remains accessible.
**Action:** When adding `.class:hover, .class:focus-visible { outline: none; }`, always append `.class:focus-visible { outline: 2px solid var(--brand); }` immediately after it.
