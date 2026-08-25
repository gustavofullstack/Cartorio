## 2024-05-18 - Pre-compute O(1) dictionary for static lists
**Learning:** O(N) array searches on static configuration lists (like CANNED_RESPONSES) are inefficient.
**Action:** Pre-compute dictionary indices ({key: value}) on module load to replace O(N) linear array searches with O(1) lookups, providing a codebase-specific performance pattern to reuse across services.
