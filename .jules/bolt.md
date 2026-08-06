## 2025-05-18 - Optimized List Query Pagination
**Learning:** In the pagination helper `list_with_pagination`, counting total items was done by loading all rows into memory with `len(db.execute(count_stmt).scalars().all())`. This is an O(N) memory anti-pattern.
**Action:** Used `db.scalar(select(func.count()).select_from(model))` for efficient counting in SQLAlchemy as documented in memories.
