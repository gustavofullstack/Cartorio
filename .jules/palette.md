## 2026-08-31 - Screen reader accessibility for dynamically populated AI extraction containers
**Learning:** Adding `aria-live="polite"` to initially hidden result containers (like `#resultContainer`) ensures screen readers smoothly announce AI-extracted content once it populates, without interrupting the user aggressively.
**Action:** Always add `aria-live="polite"` to dynamic feedback or result sections that update via JS (especially those handling async operations like AI extraction) to maintain high accessibility.
