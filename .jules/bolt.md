## 2025-02-21 - Optimize SQLAlchemy counts
**Learning:** Found an O(N) memory and data transfer anti-pattern where `len(.scalars().all())` was used to calculate the total number of items for pagination. This evaluates the entire query into memory.
**Action:** Use `func.count()` directly in the database query via `db.scalar(select(func.count()).select_from(model))` to let the database handle counting and minimize data transfer.
