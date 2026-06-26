## 2026-06-26 - Custom Swagger UI Missing Semantic Landmarks
**Learning:** Overriding default tools templates (like Swagger UI) often inadvertently removes semantic HTML landmarks and focus states. In this case, the `<div>` structure surrounding the Swagger inject element was causing accessibility issues.
**Action:** Always ensure that custom HTML injected around or wrapping third-party libraries explicitly defines basic ARIA attributes (`aria-label`) and semantic landmarks (`<header>`, `<nav>`, `<main>`), and manually adds `:focus-visible` styling for interactive wrapper components.
