## 2025-03-05 - [Optimize Static List Lookups]
**Learning:** Performing linear searches O(N) over static configuration lists like `CANNED_RESPONSES` is inefficient for repeated queries.
**Action:** Pre-compute dictionary indices `{key: value}` on module load to replace O(N) linear array searches with O(1) lookups.
