## 2026-06-27 - Swagger UI Custom HTML Formatting
**Learning:** The Swagger UI HTML string in `backend/app/main.py` is parsed via Python formatting. Therefore, adding CSS requires double escaping curly braces (`{{` and `}}`) to prevent format errors.
**Action:** When updating inline CSS in Python format strings, strictly ensure double curly braces are used.
