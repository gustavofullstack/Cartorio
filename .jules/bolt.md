## 2026-07-16 - [Optimize SQLAlchemy Counting]
 **Learning:** Using `len(db.execute(stmt).scalars().all())` to count records is highly inefficient, fetching all data into memory and causing O(N) overhead.
 **Action:** Use `func.count()` with `db.scalar(select(func.count()).select_from(model))` to perform the count directly at the database level.
