
## 2024-07-29 - Shared focus-visible and hover States in Dashboards
**Learning:** Found a specific pattern in the operations and user-review dashboards where interactive elements (`.menu button`, `.close`, `.copy-button`) share `.element:hover, .element:focus-visible { outline: none; }` rules. If we modify the shared rule to add a visible outline, it incorrectly adds a focus ring on mouse hover.
**Action:** Always preserve `outline: none;` on the shared `:hover, :focus-visible` CSS rule in this app's dashboard components, and append a distinct `.element:focus-visible` rule (e.g., `outline: 2px solid var(--brand);`) immediately after it to ensure proper keyboard accessibility without breaking the hover state.
