## 2026-09-06 - aria-live on AI Extraction Outputs
**Learning:** Dynamically populated result containers (like AI extraction outputs in the dashboard) require `aria-live="polite"` to ensure screen readers announce the newly inserted content.
**Action:** Always add `aria-live="polite"` to empty state containers that receive dynamic AI content via JavaScript DOM updates.
