## 2026-07-08 - [SQL Injection via f-string in text()]
 **Vulnerability:** Raw SQL query construction using f-strings inside SQLAlchemy's `text()` function allows for potential SQL injection vulnerabilities if inputs are not properly sanitized, and violates static analysis security rules.
 **Learning:** Dialect-specific date logic (e.g., `datetime('now', '-30 days')` vs `NOW() - INTERVAL '30 days'`) inside raw SQL queries should be avoided.
 **Prevention:** Compute dynamic values like date offsets in Python using `datetime` and `timedelta` in UTC, and pass them safely to `text()` via parameterized bound variables.
