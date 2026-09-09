## 2025-01-20 - Ensure dynamically populated result containers have aria-live
**Learning:** Dynamically populated result containers (like AI extraction outputs) require `aria-live="polite"` so screen readers announce the newly calculated values when they are populated via JavaScript.
**Action:** Add `aria-live="polite"` and `aria-atomic="true"` to dynamic output containers like `#resultContainer` and `#jsonOutput` in `backend/app/static/dashboard.html`.
