## 2026-08-20 - Optimize static lookups
**Learning:** Pre-computing dictionary indices (`{key: value}`) on module load replaces O(N) linear array searches with O(1) lookups for static configuration lists in Python (like `CANNED_RESPONSES`).
**Action:** When working with large static data arrays/tuples where items are frequently queried by specific properties, initialize dictionary mappings outside the function to create a codebase-specific performance pattern to reuse across services.
