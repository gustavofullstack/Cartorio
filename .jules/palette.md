## 2025-01-20 - Add aria-live to dynamic AI extraction outputs
**Learning:** Dynamically populated result containers (like AI extraction outputs) often lack `aria-live="polite"`, causing screen readers to miss updates.
**Action:** Ensure dynamic output containers always include `aria-live="polite"` for accessibility.
