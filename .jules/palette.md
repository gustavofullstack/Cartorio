## 2026-07-16 - Add aria-live to AI extraction outputs
**Learning:** Dynamically populated result containers, especially those rendering AI extraction outputs and JSON logs, require `aria-live="polite"` to ensure screen readers announce updates dynamically.
**Action:** Always include `aria-live="polite"` on container elements whose content is generated dynamically via JavaScript to ensure accessibility.
