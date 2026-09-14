## 2026-08-13 - SQLAlchemy efficient count
**Learning:** Loading all models into memory to count them (`len(db.execute(stmt).scalars().all())`) is an O(N) memory anti-pattern, especially on large tables (like audit logs).
**Action:** Use `db.scalar(select(func.count()).select_from(stmt.subquery()))` or `db.scalar(select(func.count()).select_from(model))` to delegate counting to the database, retrieving only the integer result.
