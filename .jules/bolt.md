## 2024-05-15 - Optimize static configuration list lookups
**Learning:** O(N) linear array searches on static configuration lists (like `CANNED_RESPONSES`) can cause unnecessary overhead when looked up frequently.
**Action:** Pre-compute dictionary indices (`{key: value}`) on module load to replace O(N) searches with O(1) lookups for static lists.
