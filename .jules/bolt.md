## 2024-05-24 - Pre-compute dictionary indices for static config lists
**Learning:** Pre-computing dictionary indices on module load for static lists (like CANNED_RESPONSES) replaces O(N) array searches with O(1) hash map lookups.
**Action:** Reused this codebase-specific performance pattern to optimize lookups and avoid linear scanning in static configurations.
