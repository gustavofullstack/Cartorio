## 2024-08-13 - Focus Visible Outline Fix
**Learning:** The application disables `outline: none` on both `:hover` and `:focus-visible` states in CSS. This is bad for accessibility because it removes the focus ring for keyboard users when navigating interactive elements.
**Action:** When applying `outline: none` on combined `:hover, :focus-visible` selectors, we must add a separate, specific rule for `:focus-visible` with a visible outline (e.g., `outline: 2px solid var(--brand);`) so keyboard navigation remains fully accessible.
