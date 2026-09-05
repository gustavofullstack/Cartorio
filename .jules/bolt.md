## 2024-05-24 - Pre-compute Dictionary Indices for Static Lists
**Learning:** When optimizing lookups for static configuration lists in Python (e.g., `CANNED_RESPONSES`), pre-computing dictionary indices (`{key: value}`) on module load replaces O(N) linear array searches with O(1) lookups. This is a codebase-specific performance pattern to reuse across backend services.
**Action:** Always prefer pre-computing dictionary indices at the module level for static lists that are frequently queried by a specific key.
