## 2026-08-09 - O(N) Memory Anti-Pattern in SQLAlchemy Counts
**Learning:** Found an anti-pattern in the codebase using `len(db.execute(stmt).scalars().all())` to count records. This brings all records into memory, which scales poorly.
**Action:** Replace `len(db.execute(stmt).scalars().all())` with `db.scalar(select(func.count()).select_from(model))` wherever found to execute count on the database level.
