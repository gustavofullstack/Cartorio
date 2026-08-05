## 2024-11-20 - [SQLAlchemy count performance]
**Learning:** Found O(N) memory anti-pattern using `len(db.execute(stmt).scalars().all())` which loads all objects into memory just to count them.
**Action:** Always use `db.scalar(select(func.count()).select_from(stmt.subquery()))` or `db.scalar(select(func.count()).select_from(model))` for efficient counting in SQLAlchemy.
