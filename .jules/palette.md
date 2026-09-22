## 2024-05-24 - Dynamic Calculation Results Need ARIA Live Regions
**Learning:** When displaying dynamic calculation results in real-time without page reloads, screen readers may not announce the newly appeared content if `aria-live` attributes are missing.
**Action:** Always wrap dynamic result containers (like `#resultContainer`) with `aria-live="polite"` and `role="region"` to ensure updates are communicated non-disruptively to assistive technologies.
