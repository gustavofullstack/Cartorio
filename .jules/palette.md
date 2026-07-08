## 2026-07-08 - Embedded HTML Templates Semantics
**Learning:** When modifying embedded HTML templates in Python files (like SWAGGER_UI_HTML in main.py), it's important to remember accessibility best practices like adding skip links, using semantic landmarks (`<main>`, `<header>`, `<nav>`), and defining clear `:focus-visible` CSS states. These string templates often lack the automated a11y tooling that frontend frameworks have.
**Action:** Always manually check embedded HTML strings for basic semantic HTML5 landmarks and keyboard navigation support when doing UX/a11y sweeps.
