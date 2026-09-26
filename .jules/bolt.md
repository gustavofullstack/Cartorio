## 2026-09-26 - Database Count Pagination Bottleneck
**Learning:** Pagination totals were fetching all rows into memory via `len(db.execute(select(model)).scalars().all())`, creating a severe memory and performance bottleneck on large tables.
**Action:** Always use database-native counting via `select(func.count()).select_from(model)` and `.scalar()` for efficient pagination counts.
