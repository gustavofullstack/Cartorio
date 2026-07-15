## 2026-07-15 - [Optimize Protocolo Number Generation]
**Learning:** Found N+1 query problem where `_gerar_numero_protocolo` loads all protocols matching a year string into memory using `.scalars().all()` just to get the length. This has O(N) memory and parsing overhead.
**Action:** Replaced `.scalars().all()` and `len()` with a SQL `COUNT(*)` via `func.count()`. This pushes computation to the DB layer, significantly reducing latency and memory usage on new protocol creation.
