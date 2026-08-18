## 2024-08-18 - Avoid O(N) linear searches in static lists for frequent lookups
**Learning:** Found O(N) array scans (`get_by_short_code` and `get_by_tag` in `chatwoot_canned_responses.py`) for accessing canned responses. While small (N=51), these linear lookups add up during text processing or macro resolutions. Refactoring to O(1) dict lookups improves perf by over ~96% (0.5s down to 0.02s per 100k calls).
**Action:** Always map static config lists to dictionary indexes (`{key: value}`) on module load when lookups are required, preventing O(N) iterations.
