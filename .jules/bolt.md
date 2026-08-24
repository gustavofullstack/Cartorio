
## 2024-05-18 - [Optimize lookup of canned responses]
**Learning:** When optimizing lookups for static configuration lists in Python (like CANNED_RESPONSES), pre-compute dictionary indices ({key: value}) on module load to replace O(N) linear array searches with O(1) lookups.
**Action:** Always pre-compute static data structures as dictionary lookups when they are frequently accessed by keys or tags.
