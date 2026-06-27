## 2026-06-27 - [N+1 Query in Router Loops]
**Learning:** Found N+1 query patterns in backend endpoints (`get_agendamentos_pendentes` and `get_agendamentos_proximos`) where database calls to fetch `Cliente` details were made individually inside a loop iterating over multiple records. Even when data is cached in redis, processing the cached records still triggers database lookups.
**Action:** Always extract foreign key IDs before a loop, execute a single batch query (using `.in_()`), build a lookup dictionary, and resolve relations in-memory.
