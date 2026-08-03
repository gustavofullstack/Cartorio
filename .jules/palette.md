## 2026-06-15 - Focus-visible overwrites on hover
**Learning:** Found an app-specific pattern where focus-visible styles were removed alongside hover styles (e.g. `.element:hover, .element:focus-visible { outline: none; }`). Simply replacing it incorrectly triggers focus rings on mouse hover.
**Action:** Always append `.element:focus-visible` as a separate rule overriding only the focus state to ensure both mouse hover and keyboard navigation states are respected.
