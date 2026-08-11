## 2026-06-15 - Preserving `:hover` intent while fixing `:focus-visible`
**Learning:** When fixing `:focus-visible` accessibility issues on elements that currently share `:hover` states with `outline: none;` (e.g., `.element:hover, .element:focus-visible { outline: none; }`), overriding the combined rule breaks the hover intent by forcing an outline on mouse interaction.
**Action:** Always preserve `outline: none;` on the combined hover/focus rule and append a new, isolated `.element:focus-visible` rule below it to accurately target keyboard navigation only.
