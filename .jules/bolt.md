## 2025-05-18 - Optimized pagination counting
**Learning:** In SQLAlchemy, fetching all objects into memory just to count them via `len(.scalars().all())` is an O(N) memory and time operation that degrades significantly as the dataset grows. This can cause severe backend latency on large tables during paginated requests.
**Action:** Use database-native counting via `select(func.count()).select_from(model)` and `.scalar()` instead of fetching all rows into memory to count elements.
