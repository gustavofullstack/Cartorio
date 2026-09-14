## 2025-05-15 - Optimize static configurations lookups
**Learning:** O(N) array searches for static configuration lists in Python (like `CANNED_RESPONSES`) can be optimized to O(1) lookups by pre-computing dictionary indices on module load.
**Action:** Replace linear iterations with dictionary `.get()` lookups for static mappings.
