## 2024-10-24 - HTML string templates in Python lack built-in semantic/A11y checks
**Learning:** Python format strings defining HTML output (e.g., Swagger UI custom wrapper) often rely heavily on generic generic `<div>` wrappers instead of semantic ones and do not undergo automated a11y tooling validation during linting.
**Action:** When inspecting Python applications, routinely check raw string literals containing HTML to ensure semantic HTML (`<header>`, `<nav>`) is used over generic tags, and manually verify keyboard accessibility states (`:focus-visible`) since linters skip them.
