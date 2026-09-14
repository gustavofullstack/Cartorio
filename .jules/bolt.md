## 2024-05-24 - Optimizing Static List Lookups
**Learning:** In Python, iterating over static configuration tuples (like CANNED_RESPONSES) for lookups is an O(N) operation. For frequently accessed data, this can become a bottleneck.
**Action:** Pre-compute dictionary indices ({key: value}) on module load to replace O(N) linear array searches with O(1) lookups. This pattern should be reused across services for static configuration lists.
