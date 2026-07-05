## $(date +%Y-%m-%d) - Double-escaping inline CSS braces in Python strings
**Learning:** The custom Swagger UI is defined as a Python string (`SWAGGER_UI_HTML`) in `backend/app/main.py` which may be processed by Python's string interpolation methods.
**Action:** All inline CSS and JavaScript curly braces within it must be double-escaped as `{{` and `}}` to prevent `KeyError` or `ValueError` crashes during string formatting.
