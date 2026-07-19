## 2026-07-19 - SQLAlchemy `len(.all())` anti-pattern

**Learning:** When retrieving the total count of rows in SQLAlchemy, loading all rows into memory via `.scalars().all()` and then applying python's `len()` introduces O(N) memory and data transfer overhead, which becomes a severe bottleneck as the table grows (especially for paginated endpoints like `list_with_pagination`).
**Action:** Always optimize SQLAlchemy counting operations by using `func.count()` directly in the database query (e.g., `db.scalar(select(func.count()).select_from(Model))`) instead of fetching all matching records.
