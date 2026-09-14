## 2026-07-11 - [N+1 Query in Agendamentos Endpoints]
**Learning:** Identified and resolved N+1 database queries in the agendamento/pendentes and agendamento/proximos endpoints. Querying inside a loop scales poorly as the number of agendamentos grows.
**Action:** Replaced loop queries with a single batch query and an in-memory dictionary lookup. This pattern should be applied proactively to list endpoints that map related data.
