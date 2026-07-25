## 2026-07-16 - Prevent SQL injection in LGPD cascade operations
**Vulnerability:** SQL Injection in dynamic table updates via f-strings (`f"UPDATE {table} SET..."`).
**Learning:** `CASCADE_TABLES` list traversal and dynamic table updates pose SQL injection risks if table names are not sanitized.
**Prevention:** Always validate dynamically injected table names using an allowlist or a regex like `re.match(r"^[a-zA-Z0-9_]+$", table)`.

## 2026-07-25 - Fix telegram test failure
**Learning:** Test assertions based on expected message response should be mindful of input validations logic. A length check () was intercepting input words, returning a different message without words like 'invalid', 'use' etc., causing assertion error.
**Prevention:** In tests providing mock text input, be aware of character length limits that might trigger fallback behaviour.

## 2026-07-25 - Fix telegram test failure
**Learning:** Test assertions based on expected message response should be mindful of input validations logic. A length check (`len(tl) > 10`) was intercepting input words, returning a different message without words like "invalid", "use" etc., causing assertion error.
**Prevention:** In tests providing mock text input, be aware of character length limits that might trigger fallback behaviour.
