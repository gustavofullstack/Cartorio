## 2026-09-23 - SQLAlchemy In-Memory Count Performance Fix
**Learning:** Using `len(db.execute(select(model)).scalars().all())` fetches all records into memory, which causes severe memory and performance bottlenecks on large tables.
**Action:** Always use database-native counting via `select(func.count()).select_from(model)` and `.scalar()` for total row counts, especially in pagination helpers.
