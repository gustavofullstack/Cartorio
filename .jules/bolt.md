## 2024-05-18 - [Optimization of `COUNT` queries in SQLite vs Postgres]
**Learning:** In SQLAlchemy, executing `select(Model.column).scalars().all()` and then applying `len()` fetches all records into application memory. Using `func.count(Model.id)` is faster, memory-efficient, and correctly defaults to `0` instead of `None` without needing `len()`. Also, I must ensure `.scalar()` or `.scalar_one_or_none()` is used for scalar returns.
**Action:** Always prefer `func.count(Model.id)` over Python-level `len()` when calculating aggregate sums or lengths of database table entries.
