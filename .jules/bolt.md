## 2026-08-02 - Optimize SQLAlchemy counting
**Learning:** Using `func.count()` in SQLAlchemy queries avoids O(N) memory and data transfer overhead compared to fetching all matching records with `.scalars().all()` and calculating their `len()`.
**Action:** Always use `func.count()` for counting operations in database queries.
