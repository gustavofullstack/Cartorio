## 2024-08-30 - O(1) Lookup for Static Configurations
**Learning:** In backend services, static configuration lists (like `CANNED_RESPONSES`) were being queried using O(N) array searches. This is a common pattern that can be optimized by pre-computing dictionary indices on module load for O(1) lookups.
**Action:** Always prefer pre-computing dictionaries mappings (e.g., `{key: value}`) for static data that requires frequent lookups instead of doing linear searches, drastically improving performance.
