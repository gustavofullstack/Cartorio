## 2026-07-07 - Custom Swagger UI Accessibility
**Learning:** Custom Swagger UI configurations in backend services (like FastAPI) often lack proper semantic HTML structure (e.g., `<header>`, `<nav>`) and focus styles since they are custom strings appended to default UI bundles, which negatively impacts keyboard and screen reader accessibility on the API documentation page.
**Action:** Always check custom HTML string templates in Python backends for basic semantic tags and focus states when they expose internal tooling UI.
