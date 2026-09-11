## 2025-03-26 - O(1) Lookup Indexing for Static Lists
**Learning:** In backend services, static configuration lists (like `CANNED_RESPONSES`) searched linearly (O(N)) can cause performance bottlenecks.
**Action:** Pre-compute dictionary indices (`{key: value}`) on module load for O(1) lookups instead of doing linear array searches on every request.
