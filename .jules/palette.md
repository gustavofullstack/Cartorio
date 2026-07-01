## 2026-06-30 - Accessible inline custom UI templates
**Learning:** When embedding custom UI modifications strictly within backend Python string templates (e.g., custom Swagger UI rendering in `backend/app/main.py`), CSS and JavaScript curly braces must be double-escaped as `{{` and `}}` to avoid string interpolation errors.
**Action:** When adding accessibility styles like `:focus-visible` in python strings, always double-escape curly braces, and use semantic html landmarks for embedded UI templates to ensure screen reader support.
