## 2025-02-13 - Add aria-live to dynamically populated result containers
**Learning:** Dynamically populated AI result containers, such as payload and breakdown sections, need `aria-live="polite"` so screen readers can properly announce changes without disturbing the user's flow.
**Action:** Add `aria-live="polite"` attributes to containers (`#resultContainer`, `#jsonOutput`) where AI responses or calculation breakdowns are injected after user interaction.
