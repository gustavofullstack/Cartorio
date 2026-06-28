## 2026-06-28 - Custom UI Templates in Python APIs
**Learning:** When extending UI templates defined as strings directly within a Python application (like custom Swagger UI layouts), standard inline CSS with curly braces `{}` can conflict with Python's string interpolation.
**Action:** Always ensure that inline CSS and JavaScript braces are double-escaped (e.g., `{{` and `}}`) within Python string templates to prevent `KeyError` or formatting errors when the string is parsed.
