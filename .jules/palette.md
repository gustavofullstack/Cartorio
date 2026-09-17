## 2024-05-24 - Interactive Accessibility in Dynamic Containers
**Learning:** Dynamically updated containers (like AI extraction outputs) require `aria-live="polite"` so screen readers announce changes, and interactive elements need proper focus states leveraging existing variables (e.g. `var(--bg-dark)` and `var(--primary-light)`) for high-contrast visibility.
**Action:** Always add `aria-live` to dynamically updated result containers and ensure `focus` and `focus-visible` states use double box-shadows using existing CSS variables.
