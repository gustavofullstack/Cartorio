## 2024-08-15 - Interactive Element Focus Rings Override
**Learning:** Found a widespread CSS pattern where interactive elements like `.close`, `.copy-button`, and dropdown menus `.menu button` have their default outline overridden with `outline: none` for combined `:hover, :focus-visible` pseudo-classes.
**Action:** Always append an explicit `.selector:focus-visible { outline: 2px solid var(--brand); }` rule to ensure keyboard accessibility.
