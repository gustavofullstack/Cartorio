
## 2024-07-30 - Optimize SQLAlchemy counting
**Learning:** Using `len(db.execute(stmt).scalars().all())` is an O(N) memory and data transfer anti-pattern, as it loads all matching records into memory just to count them.
**Action:** Use `func.count()` with `db.scalar(select(func.count()).select_from(model))` for counts when the objects aren't needed for iteration.
