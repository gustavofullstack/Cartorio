## 2026-09-22 - Replacing in-memory count with database-native count

**Learning:** SQLAlchemy's `len(db.execute(stmt).scalars().all())` is an anti-pattern for counting rows because it fetches all rows into Python memory just to count them. This becomes a major performance bottleneck for large tables (like `AuditLog`).
**Action:** Always use `select(func.count()).select_from(model)` and `.scalar()` for retrieving total counts to leverage database-native counting (e.g., `COUNT(*)`).
