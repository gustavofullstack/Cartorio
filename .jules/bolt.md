## 2026-06-28 - Optimizing regex passes in PII scrubbing
**Learning:** In highly called internal services like PII scrubbing, using separate `pattern.findall()` and `pattern.sub()` calls results in duplicate regex execution. Also, doing `if p.findall()` and `len(p.findall())` executes the regex twice.
**Action:** Use `pattern.subn()` to apply replacements and get the count in a single pass. Use the walrus operator `(m := pattern.findall())` to execute the match only once when both existence and matches are needed. This cuts execution time for heavily-regexed functions in half.
