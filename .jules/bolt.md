## 2024-08-07 - Avoid loading all scalar models when counting
**Learning:** In SQLAlchemy 2.0, counting rows by executing `len(db.execute(stmt).scalars().all())` is an O(N) memory anti-pattern as it needlessly fetches all matching ORM objects from the database just to count them.
**Action:** When counting rows, always use `db.scalar(select(func.count()).select_from(model))` to perform the count entirely on the database side and avoid loading instances into memory.
