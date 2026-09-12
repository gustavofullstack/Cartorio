## 2024-09-12 - Pre-computing index for O(1) lookups in static lists

**Learning:** In backend modules containing large static configuration lists like `CANNED_RESPONSES`, doing `O(N)` linear array searches (e.g., `for r in CANNED_RESPONSES: if r.short_code == code`) for lookups is an anti-pattern. Pre-computing dictionary indices on module load replaces it with `O(1)` dictionary lookups. This codebase-specific performance pattern is recommended to reuse across backend services.
**Action:** When finding static lists, create a mapping dict initialized at module load for `O(1)` lookups.
