## 2026-07-09 - [N+1 API Query Fix]
**Learning:** Found N+1 queries in `backend/app/api/v1/router.py` within `get_agendamentos_pendentes` and `get_agendamentos_proximos` loops, which query individual client details inside a loop iterating over multiple appointments. This slows down API execution due to excessive database requests inside loop processing.
**Action:** When finding iterative lookups in endpoints, always pre-fetch the related data using batch operations (e.g., `in_` clauses) and map them by IDs before entering the processing loop.
