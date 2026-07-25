## 2026-07-16 - Prevent SQL injection in LGPD cascade operations
**Vulnerability:** SQL Injection in dynamic table updates via f-strings (`f"UPDATE {table} SET..."`).
**Learning:** `CASCADE_TABLES` list traversal and dynamic table updates pose SQL injection risks if table names are not sanitized.
**Prevention:** Always validate dynamically injected table names using an allowlist or a regex like `re.match(r"^[a-zA-Z0-9_]+$", table)`.
