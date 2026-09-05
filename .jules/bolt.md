## 2024-05-24 - Pre-compute dictionary indices for static lists
**Learning:** When searching static configuration lists in Python (e.g., `CANNED_RESPONSES`), an O(N) linear array search can be replaced with an O(1) lookup by pre-computing dictionary indices (`{key: value}`) on module load.
**Action:** When working with codebase-specific static configuration lists, reuse this performance pattern to eliminate O(N) lookups across backend services.
