
## 2024-05-24 - Screen Reader Accessibility for AI Extraction
**Learning:** Dynamically populated AI extraction results are not automatically announced to screen readers, leaving visually impaired users unaware when data is updated.
**Action:** Always add `aria-live="polite"` to dynamically updated AI extraction result containers to ensure content changes are announced.
