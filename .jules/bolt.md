## 2025-01-24 - Pre-compute static list indices for O(1) lookups
**Learning:** Found O(N) array searches in Python for static configuration lists like `CANNED_RESPONSES`. While lists are short (50+ items), this is a codebase-specific pattern where these static configurations can be heavily queried.
**Action:** Always pre-compute dictionary indices `{key: value}` on module load for static lists to replace O(N) linear array searches with O(1) dictionary lookups. This improves endpoint efficiency and reduces CPU cycles during frequent text matching operations.
