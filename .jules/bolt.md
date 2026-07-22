## 2026-07-22 - Optimize database row counting
**Learning:** Fetching all matching records with `.scalars().all()` just to calculate `len()` incurs O(N) memory and data transfer overhead, creating a bottleneck for pagination queries on large datasets.
**Action:** Use `func.count()` directly in the database query (e.g., `db.scalar(select(func.count()).select_from(Model))`) for efficient counting without fetching unnecessary objects.
