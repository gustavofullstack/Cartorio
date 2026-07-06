## 2026-07-06 - N+1 Query in Protocolos
**Learning:** List comprehension returning data accessing related model properties (like `p.cliente.nome`) easily triggers N+1 queries if relationships aren't eagerly loaded in SQLAlchemy, even on supposedly "lightweight" endpoints returning denormalized dictionaries.
**Action:** Always verify relationship access loops; use `.options(contains_eager(...))` alongside `.join()` to prevent N+1 without extra subqueries.
