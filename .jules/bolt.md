## 2024-05-24 - Database count optimization
**Learning:** Fetching all rows via `len(.scalars().all())` is an O(N) operation in memory and DB time.
**Action:** Always use database-native counting via `select(func.count()).select_from(model)` and `.scalar() or 0` to avoid memory and performance bottlenecks, especially for pagination endpoints.
