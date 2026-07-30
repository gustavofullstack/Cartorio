## 2024-08-01 - Avoid Focus Rings on Mouse Hover
**Learning:** Fixing :focus-visible issues on elements sharing :hover states (e.g. .element:hover, .element:focus-visible { outline: none; }) by replacing outline:none with a visible outline incorrectly shows the ring on hover.
**Action:** Preserve outline:none on the combined rule, and append a new, distinct rule specifically for focus: .element:focus-visible { outline: 2px solid var(--brand); }
