## 2025-01-20 - Fix memory bottleneck in pagination counting
**Learning:** Found a generic pagination helper `list_with_pagination` in `backend/app/api/v1/_helpers.py` that fetched all rows into memory via `len(.scalars().all())` to calculate the total count, causing severe memory and performance bottlenecks on large tables.
**Action:** Always use database-native counting via `select(func.count()).select_from(model)` and `.scalar()` instead of fetching all rows to memory.
