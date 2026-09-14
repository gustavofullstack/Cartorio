## 2024-05-24 - SQLAlchemy Count Optimization
**Learning:** Found an O(N) memory anti-pattern in SQLAlchemy queries: `len(db.execute(stmt).scalars().all())`. This unnecessarily loads all matching objects into memory just to count them.
**Action:** Replace `len(db.execute(stmt).scalars().all())` with `db.scalar(select(func.count()).select_from(model))` or `db.scalar(select(func.count()).select_from(stmt.subquery()))` for efficient O(1) memory counting in SQLAlchemy.
