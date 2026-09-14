## 2026-09-14 - Accessible Dynamic AI Results
**Learning:** Dynamically populated AI extraction results are invisible to screen readers without live regions, leaving visually impaired users unaware when data finishes generating or changes.
**Action:** Always ensure dynamically populated result containers include `aria-live="polite"` to proactively announce updates to assistive technologies.
