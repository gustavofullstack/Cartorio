## 2024-09-13 - Optimize pagination total count query
**Learning:** Using `len(db.execute(select(model)).scalars().all())` to get the total count for pagination fetches all rows into memory, causing a massive N+1-like memory bottleneck as tables grow.
**Action:** Always use database-native counting with `db.execute(select(func.count()).select_from(model)).scalar()` to avoid fetching unnecessary rows into memory.
