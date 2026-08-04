
## 2026-08-04 - Fix hover and focus-visible combination
**Learning:** When `:focus-visible` accessibility issues are fixed on elements that share `:hover` states with `outline: none`, do not replace `outline: none` in the combined rule because it will incorrectly show the focus ring on mouse hover.
**Action:** Preserve `outline: none` in the combined rule and append a new, distinct rule specifically for focus: `.element:focus-visible { outline: 2px solid var(--ink); }`
