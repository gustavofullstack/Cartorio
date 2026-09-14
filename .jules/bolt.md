## 2024-05-30 - O(1) Lookups for Static Lists
**Learning:** In the backend `CANNED_RESPONSES` static list (and similar configuration lists), linear array searches `O(N)` were being used for lookups via `get_by_short_code()`. This results in slower lookup times than necessary, which can impact performance at scale when resolving tags or codes repeatedly.
**Action:** Pre-compute a dictionary index `{key: value}` on module load to replace `O(N)` linear array searches with `O(1)` dictionary lookups. This pattern is effective and safe for read-only static configuration lists in Python.
