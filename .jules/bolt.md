## 2024-09-10 - Pre-compute dictionary for static lookups
**Learning:** Optimizing lookups for static configuration lists in Python (e.g., `CANNED_RESPONSES`) by pre-computing dictionary indices on module load replaces O(N) linear array searches with O(1) lookups. This is a codebase-specific performance pattern to reuse across backend services.
**Action:** Always pre-compute dictionaries for lookup functions based on static lists.
