## 2024-10-24 - Accessibility improvements for dynamic content
**Learning:** Dynamically populated result containers (like AI extraction outputs) require `aria-live="polite"` for screen readers to announce new content gracefully.
**Action:** Always add `aria-live` attributes to dynamic output containers.
