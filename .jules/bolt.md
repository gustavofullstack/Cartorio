## 2026-07-28 - Avoid len(.all()) anti-pattern in SQLAlchemy
**Learning:** Using `len(db.execute(count_stmt).scalars().all())` fetches all matching rows from the database just to count them. This is an O(N) memory and data transfer bottleneck, especially critical for pagination queries where N could be millions.
**Action:** Always use `func.count()` directly in the database query (e.g., `db.scalar(select(func.count()).select_from(count_stmt.subquery()))`) to push the counting operation to the database level.
