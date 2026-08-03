## 2025-08-03 - [Optimize Pagination COUNT]
**Learning:** In SQLAlchemy, calculating `len(db.execute(select(...)).scalars().all())` fetches all matching rows into memory, which causes O(N) memory and data transfer overhead for large datasets.
**Action:** Use `db.scalar(select(func.count()).select_from(model))` or similar for counting records directly in the database.
