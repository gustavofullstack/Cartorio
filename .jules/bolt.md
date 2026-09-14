## 2026-08-29 - O(1) Static Configuration Indices
**Learning:** In backend Python services, static configuration lists (like `CANNED_RESPONSES`) were using O(N) linear array searches per request to look up items by ID/code.
**Action:** When optimizing lookups for static configuration lists in Python, pre-compute dictionary indices (`{key: value}`) on module load to replace O(N) linear array searches with O(1) lookups, providing a codebase-specific performance pattern to reuse across services.
