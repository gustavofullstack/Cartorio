## 2026-09-17 - Optimize SQLAlchemy Count
**Learning:** Using len(.scalars().all()) fetches all rows into memory, causing a performance bottleneck. Use select(func.count()) and .scalar() instead.
**Action:** Always use database-native counting for pagination.
