## 2026-09-05 - Optimize lookup for static configuration lists
**Learning:** When dealing with static configuration lists in Python (e.g., CANNED_RESPONSES), linear searches (O(N)) can become a bottleneck as the list grows.
**Action:** Pre-compute dictionary indices ({key: value}) on module load to replace O(N) linear array searches with O(1) hash map lookups. This is a codebase-specific performance pattern to reuse across backend services.
