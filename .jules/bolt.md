
## 2026-07-16 - [Optimize SQLAlchemy Count in list_with_pagination]
**Learning:** Using `len(db.execute(select(model)).scalars().all())` to get a total row count causes SQLAlchemy to instantiate ORM objects for every row matching the query and loads all data into memory, resulting in O(N) memory and data transfer overhead. This architecture flaw can cause significant slowdowns or memory exhaustion as data tables grow.
**Action:** Always use `db.scalar(select(func.count()).select_from(model))` to perform database-native counting efficiently (O(1) data transfer to Python), avoiding full query execution and object loading.
