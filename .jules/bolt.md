## 2026-07-05 - N+1 Query in Protocolo API
**Learning:** Returning objects with lazy loaded relationships from API endpoints can cause severe N+1 query problems because SQLAlchemy emits an extra query for every object serialization when the attribute is accessed.
**Action:** When using joins (`.join(...)`) in a SQLAlchemy query to fetch related records needed by the API serialization (e.g. `Protocolo.cliente.nome`), always pair it with an eager loading option like `.options(contains_eager(Protocolo.cliente))` to reuse the data fetched in the JOIN and prevent N+1 queries.
