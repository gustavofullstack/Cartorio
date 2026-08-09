## 2024-08-09 - Keyboard Accessibility with outline: none

**Learning:** When applying `outline: none;` to combined `:hover, :focus-visible` states to prevent focus rings on mouse clicks, it breaks keyboard accessibility because the focus indicator is completely removed for keyboard users.
**Action:** Always append a separate, distinct rule exclusively for `:focus-visible` (e.g., `outline: 2px solid var(--brand);`) immediately after the combined rule to ensure keyboard navigation remains accessible.