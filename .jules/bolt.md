## 2024-11-20 - [SQLAlchemy Counting Pattern]
**Learning:** For efficient counting in SQLAlchemy, never use `len(db.execute(stmt).scalars().all())`. It is an O(N) memory anti-pattern that loads all matching rows into Python memory before counting, crashing with large datasets.
**Action:** Always use `db.scalar(select(func.count()).select_from(model))` for table-level counting, or `db.scalar(select(func.count()).select_from(stmt.subquery()))` when counting rows for complex queries.
