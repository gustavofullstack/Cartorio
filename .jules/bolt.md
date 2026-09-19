## 2025-01-20 - Fast pagination count
**Learning:** Using `len(db.execute(stmt).scalars().all())` fetches all rows into memory and performs the count on the application side. This scales terribly with larger tables and creates an N+1 like performance bottleneck for memory / compute since the database can do it natively and faster.
**Action:** Always use database-native counting via `select(func.count()).select_from(model)` and `.scalar()` instead of fetching all rows into memory.
