## 2025-10-24 - Database Native Counts
**Learning:** Using `len(db.execute(stmt).scalars().all())` fetches all rows into memory just to get a total count, which severely bottlenecks memory and CPU on pagination lists.
**Action:** Always use database-native counting with `select(func.count()).select_from(model)` and `.scalar()` to avoid loading unneeded rows into memory.
