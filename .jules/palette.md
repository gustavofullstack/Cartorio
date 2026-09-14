## 2024-08-24 - Missing Focus State on Primary Action Button
**Learning:** Found that the primary call-to-action button in the dashboard calculator lacks a `focus-visible` state, meaning keyboard users do not receive visual feedback when tabbing to this critical interaction element. Also missing a subtle disabled/loading state indication.
**Action:** Always ensure `.btn-action` or equivalent primary buttons have an explicit `:focus-visible` outline in the CSS to preserve keyboard accessibility.
