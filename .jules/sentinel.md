## 2025-02-09 - Parameterize SQL queries safely to prevent SQL Injection

**Vulnerability:** SQL Injection via Python f-strings used inside SQLAlchemy's `text()` function.
**Learning:** Using f-strings to concatenate string literals directly into SQL code, even when intended for dialect-specific values like date/time functions, bypasses standard parameterization mechanisms.
**Prevention:** Instead of injecting raw SQL via strings, handle date computations programmatically using native Python libraries (e.g. `datetime` and `timedelta`) and pass those variables directly to `db.execute` utilizing SQLAlchemy's safe variable bindings (`{"var": var}`).
