## 2024-05-24 - Accessible Dynamic Contents
**Learning:** Dynamically populated result containers (like AI extraction outputs) are invisible to screen readers without specific ARIA attributes, causing an accessibility issue pattern in this app's dynamic dashboards.
**Action:** Always include `aria-live="polite"` on dynamic output containers to ensure screen readers reliably announce content updates.
