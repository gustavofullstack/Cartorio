## 2024-03-22 - Use database-native counting in SQLAlchemy
**Learning:** Using `len(db.execute(select(model)).scalars().all())` fetches all rows into memory just to count them, causing massive memory footprint and slow performance for large tables.
**Action:** Always use database-native counting with `select(func.count()).select_from(model)` and `.scalar()` to perform the aggregation in the database.
