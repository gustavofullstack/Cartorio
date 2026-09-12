## 2026-06-25 - Dynamically populated AI results need aria-live
**Learning:** In this app, result containers for AI extractions (like `#resultContainer`) are populated dynamically and revealed to the user. Without `aria-live`, screen reader users are not notified when the result appears.
**Action:** Always add `aria-live="polite"` to dynamically populated result containers (like AI extraction outputs) for screen reader accessibility, as per memory rules.
