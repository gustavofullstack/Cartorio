## 2026-07-15 - SQLAlchemy Counting Memory Anti-pattern
**Learning:** Using `len(db.execute(stmt).scalars().all())` is an O(N) memory anti-pattern that unnecessarily loads all matching objects into memory just to count them. This is especially problematic for endpoints using pagination where the total count query needs to evaluate large datasets.
**Action:** Always use `db.scalar(select(func.count()).select_from(stmt.subquery()))` or similar for database-side O(1) memory counting in SQLAlchemy 2.0.
