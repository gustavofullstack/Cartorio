## 2026-07-13 - Optimize SQLAlchemy Counting
**Learning:** Using `len(db.execute(stmt).scalars().all())` fetches all matching rows into memory, causing severe O(N) memory and data transfer overhead, particularly for endpoints that generate sequential identifiers (like `Protocolo`).
**Action:** Always use `db.scalar(select(func.count()).select_from(Model).where(...))` for counting operations instead of loading the records into memory.
