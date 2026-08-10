## 2024-08-10 - O(N) memory anti-pattern in SQLAlchemy counting
**Learning:** Found instances where `len(db.execute(stmt).scalars().all())` was used for counting rows. This is an O(N) memory anti-pattern that unnecessarily loads all matching objects into memory just to count them, severely impacting performance on large datasets.
**Action:** Always use `db.scalar(select(func.count()).select_from(model))` or `db.scalar(select(func.count()).select_from(stmt.subquery()))` to perform efficient SQL-level counting and retrieve just the integer value.
