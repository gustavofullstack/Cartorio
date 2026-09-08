## 2024-09-08 - Optimize Canned Responses Lookups
**Learning:** Static configuration arrays (like `CANNED_RESPONSES`) accessed frequently via O(N) linear scans cause a significant performance overhead (~20x slower for 50 items).
**Action:** Pre-compute dictionary indices (`{key: value}`) on module load to replace O(N) searches with O(1) lookups for fields like `short_code` and `tags`.
