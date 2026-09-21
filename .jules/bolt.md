## 2024-10-24 - SQLAlchemy counting optimization
**Learning:** Retrieving total counts for pagination or other purposes in SQLAlchemy should always use database-native counting via `select(func.count()).select_from(model)` and `.scalar()` instead of fetching all rows into memory (e.g., using `len(.scalars().all())`) to avoid memory and performance bottlenecks.
**Action:** Always prefer `func.count()` for aggregation instead of python `len()` on large queries.
