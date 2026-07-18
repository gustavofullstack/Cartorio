## 2026-07-28 - Optimize pagination count query
**Learning:** Using `len(db.execute(stmt).scalars().all())` for counting total records in SQLAlchemy pagination is an anti-pattern. It fetches all rows into memory, resulting in O(N) memory and transfer overhead.
**Action:** Use `db.scalar(select(func.count()).select_from(model))` to perform counting directly in the database (O(1) memory overhead).