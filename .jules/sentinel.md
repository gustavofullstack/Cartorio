## 2025-02-28 - Fix SQL injection risk in raw SQL
**Vulnerability:** Raw SQL execution using f-string interpolation for temporal data limits in LGPD APIs (`backend/app/api/v1/lgpd_direitos_v2.py`).
**Learning:** Dialect specific logic relying on raw SQL strings (e.g. `NOW()` vs `datetime('now')`) is risky and error-prone compared to relying on proper parameter bindings and Python standard libraries. Using f-strings into `.execute(text())` can often bypass basic SQLi mitigations.
**Prevention:** Use standard Python libraries (`datetime`, `timedelta`) for generic data generation, and always use SQLAlchemy's parameterized execution bindings (e.g., `:param_name` in `text()` + `{"param_name": val}`) to keep user and environment inputs isolated from the query execution logic.
