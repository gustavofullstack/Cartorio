## 2024-05-24 - O(1) Lookups for Static Lists
**Learning:** Pre-computing dictionary indices (`{key: value}`) on module load replaces O(N) linear array searches with O(1) lookups for static configuration lists (like `CANNED_RESPONSES`), providing a codebase-specific performance pattern to reuse across services.
**Action:** Always use pre-computed dictionaries for frequent lookups on static lists instead of linear iteration.
