## 2026-08-08 - Optimized list_with_pagination
**Learning:** Found a memory anti-pattern where len(db.execute(stmt).scalars().all()) was used to count results, which unnecessarily loads all objects into memory.
**Action:** Replaced with db.scalar(select(func.count()).select_from(stmt.subquery())) to perform the count operation efficiently inside the database.
