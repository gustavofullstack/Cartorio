## 2024-08-15 - [O(N) Memory Count Query Pattern]
**Learning:** Found a systemic anti-pattern in `list_with_pagination` where counting total records was loading the entire result set into memory (`len(db.execute(count_stmt).scalars().all())`). In SQLAlchemy, this is an O(N) memory leak and performance bottleneck for large datasets.
**Action:** Replaced with `select(func.count()).select_from(model)` and `db.scalar()` to execute an efficient `SELECT COUNT(*)` on the database side, solving the memory and database load issue.
