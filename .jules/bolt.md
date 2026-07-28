## 2026-07-28 - Optimize pagination counting in list_with_pagination
**Learning:** Using `len(db.execute(count_stmt).scalars().all())` to count records causes severe memory and data transfer overhead by fetching all records just to count them, especially in pagination queries which are frequently used.
**Action:** Always use `db.scalar(select(func.count()).select_from(model))` to let the database do the counting efficiently at the SQL level.
