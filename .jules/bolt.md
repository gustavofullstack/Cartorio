## 2024-08-15 - SQLAlchemy Counting O(N) memory anti-pattern
**Learning:** Using `len(db.execute(stmt).scalars().all())` is an O(N) memory anti-pattern that unnecessarily loads all matching objects into memory, creating significant performance bottlenecks on large datasets.
**Action:** For efficient counting in SQLAlchemy, always use `db.scalar(select(func.count()).select_from(model))` or `db.scalar(select(func.count()).select_from(stmt.subquery()))`. Never use `len()`.
