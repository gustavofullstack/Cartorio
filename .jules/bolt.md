## 2026-06-29 - [Avoid all() on append-only logs for memory efficiency]
**Learning:** Using `all()` on tables that grow indefinitely (such as `AuditLog` for LGPD requirements) leads to unbound memory consumption when reading the entire chain into memory.
**Action:** Always prefer `yield_per(1000)` over `all()` when querying the entire log (e.g., verifying an append-only hash chain) to drastically reduce memory usage (proven reduction from 18.94 MB to 0.75 MB for 10000 records).
