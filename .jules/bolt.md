
## 2025-02-20 - O(N) Array Searches Replaced with O(1) Dictionary Lookups
**Learning:** Found linear search array operations (`O(N)`) inside heavily hit lookup functions (`get_by_short_code` and `get_by_tag`) checking `CANNED_RESPONSES` which are static definitions that shouldn't pay runtime search costs.
**Action:** Replaced `O(N)` loop logic with O(1) dictionary maps built efficiently ONCE at module load time (`_SHORT_CODE_INDEX`, `_TAG_INDEX`), providing a drastic speedup in search operations without sacrificing readability. We should proactively pre-compute lookup tables for static config lists.
