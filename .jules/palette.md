## 2024-08-15 - Focus Rings Keyboard Navigation
**Learning:** For UI accessibility in this codebase, when applying `outline: none;` to combined `:hover, :focus-visible` states to prevent focus rings on mouse clicks, it breaks keyboard navigation accessibility.
**Action:** Always append a separate, distinct rule exclusively for `:focus-visible` (e.g., `outline: 2px solid var(--brand);`) to ensure keyboard navigation remains accessible.
