## 2024-09-19 - Added aria-live to dashboard result container
**Learning:** Dynamic content updates (like the appearance of `#resultContainer` after processing an extraction) are not automatically announced by screen readers, creating a significant accessibility gap for visually impaired users.
**Action:** Always add `aria-live="polite"` to containers that are populated or revealed dynamically with critical results, ensuring screen readers announce the changes without disrupting the user's workflow.
