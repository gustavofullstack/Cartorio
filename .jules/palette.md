## 2024-03-20 - Adding aria-live to dynamic content
**Learning:** For dynamically populated result containers (like AI extraction outputs and stat cards) in this app, ensure they include `aria-live="polite"` for screen reader accessibility so changes are announced without interrupting the user.
**Action:** Always add `aria-live="polite"` to dynamic content areas where live data is fetched and displayed.
