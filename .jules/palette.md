## 2026-06-30 - Enhanced Semantic Accessibility in Swagger UI
**Learning:** Custom UI views generated from backend string templates often lack semantic HTML (`<header>`, `<nav>`) and focus states for keyboard navigation.
**Action:** Replaced `div` tags with semantic elements and added `:focus-visible` styling to custom API docs. Always check inline CSS for `focus-visible` states when adding custom headers.
