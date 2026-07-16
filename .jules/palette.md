## 2026-07-16 - Add Semantic HTML and Skip Link to Embedded Swagger UI
**Learning:** Python f-strings used for embedded HTML templates can inadvertently cause invalid syntax when adding CSS styles, as curly braces `{` and `}` are parsed as f-string expression boundaries.
**Action:** When adding keyboard accessibility styles (`:focus-visible` or `.skip-link`) to an HTML template within a Python f-string, always double-escape the curly braces as `{{` and `}}` to ensure they are rendered correctly as CSS block delimiters and maintain valid Python syntax.
