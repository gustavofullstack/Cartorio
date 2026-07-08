## 2024-05-18 - Parameterize Date Queries in SQLAlchemy text()
 **Vulnerability:** SQL Injection via f-strings in `text()`
 **Learning:** When executing raw SQL with SQLAlchemy's `text()`, avoid injecting dialect-specific SQL functions or expressions via f-strings.
 **Prevention:** To ensure cross-dialect compatibility (e.g., SQLite in tests vs. PostgreSQL in production) and prevent SQL injection, compute dynamic values like date offsets in Python (using `datetime` and `timedelta`) and pass them safely as bound parameters.
