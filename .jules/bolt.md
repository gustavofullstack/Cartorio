## 2024-07-21 - Optimize pagination counting
**Learning:** Found an instance in `backend/app/api/v1/_helpers.py` where a pagination count query (`list_with_pagination`) loaded all records into memory using `db.execute(count_stmt).scalars().all()` and then called `len()` on the list.
**Action:** Replaced the memory-heavy list loading with a direct SQLAlchemy O(1) query `select(func.count()).select_from(model)` mapped to `db.scalar()`. Avoid `.all()` when only counting is needed.
