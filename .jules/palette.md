## 2026-07-28 - Focus Visible Accessibility
**Learning:** Found an anti-pattern in the CSS: `:hover` and `:focus-visible` share the same rule which sets `outline: none;` without providing an alternative focus indicator. Example: `.menu button:hover, .menu button:focus-visible { outline: none; }`
**Action:** When fixing `:focus-visible` issues, keep `outline: none;` on the combined rule to avoid adding a focus ring on hover, and append a new distinct rule for focus: `.element:focus-visible { outline: 2px solid var(--brand); }`.
