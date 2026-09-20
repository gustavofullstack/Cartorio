## 2024-05-20 - Missing ARIA label for prompt input
**Learning:** The textarea for natural language input does not have an ARIA label or an explicit association via the 'for' attribute of a label that matches the textarea's ID.
**Action:** Ensure inputs are explicitly associated with their labels or use aria-label.

## 2024-05-20 - Missing aria-live for dynamically updated results
**Learning:** The results of the AI extraction are displayed dynamically via JavaScript, but the container lacks `aria-live="polite"` to notify screen readers of the update.
**Action:** Add `aria-live="polite"` to dynamic result containers.
