## 2026-07-27 - Optimize count query with func.count()
**Learning:** Using len(.scalars().all()) for counting operations creates an N+1 memory bottleneck by fetching all records just to count them.
**Action:** Use func.count() at the database level instead of counting in-memory.
