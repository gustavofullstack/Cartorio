## 2024-07-25 - [Semantic HTML for Custom Swagger UI]
**Learning:** When custom Swagger UI is injected via raw Python HTML strings, generic div tags are often used for layout rather than semantic HTML, negatively impacting screen reader navigation and omitting visual focus states for keyboard users navigating documentation.
**Action:** Audit raw HTML injections (like `SWAGGER_UI_HTML`) for missing ARIA attributes, semantic structure (`<header>`, `<nav>`), and keyboard `:focus-visible` styling, ensuring accessibility parity with standard React/TS components.
