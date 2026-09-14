## 2025-02-18 - Improve AI Extraction Output Accessibility
**Learning:** Dynamically populated AI extraction outputs (like JSON payloads and financial breakdowns) need `aria-live="polite"` so screen readers can announce changes seamlessly. Also, custom interactive elements need explicit, high-contrast `:focus-visible` states using double box-shadows.
**Action:** Added `aria-live="polite"` to dynamically updated AI result containers and applied a double box-shadow using `var(--bg-dark)` and `var(--primary-light)` for `:focus-visible` on form elements and buttons.
