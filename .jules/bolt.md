## 2026-09-06 - Pre-computed lookup dicts for canned responses
**Learning:** For static, long lists (e.g. `CANNED_RESPONSES` configuration tuple) that get frequently searched by key, always create a pre-computed dictionary lookup index at module-load time. This avoids $O(N)$ linear array searches dynamically and allows fast $O(1)$ lookup resolutions.
**Action:** When designing a lookup from static tuples with unique fields (like short_codes), compute a module-level index.
