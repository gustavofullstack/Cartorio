## 2026-07-13 - [Fix SQL Injection Risk in Date Queries]
 **Vulnerability:** Unsafe string interpolation (f-strings) inside `sqlalchemy.text()` execution in LGPD dashboard endpoints.
 **Learning:** Date calculation specific to database dialects (e.g. `datetime('now')` vs `NOW()`) was hardcoded dynamically using f-strings inside raw SQL statements. While not immediately exploitable via user input, this violates secure coding practices by breaking parameterized querying and flagging SAST tools.
 **Prevention:** Compute dynamic values like dates safely using Python (`datetime.now()`, `timedelta()`) and pass them using bound parameters (`:parameter_name`) in the `db.execute()` calls to ensure cross-dialect compatibility and prevent SQL injection.
