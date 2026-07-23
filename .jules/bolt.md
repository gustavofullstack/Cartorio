## 2024-05-24 - Avoid O(N) SQLAlchemy len(.all()) for Counts
**Learning:** Using `len(.all())` for pagination counting reads all rows into memory, causing severe performance issues.
**Action:** Use `func.count()` directly in the database query instead.
