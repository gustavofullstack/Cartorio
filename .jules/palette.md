## 2026-08-21 - Fix Interactive Divs
**Learning:** Using `role="status"` on a clickable `div` instead of a native `<button>` prevents keyboard access and misleads screen readers about interactivity.
**Action:** Always replace pseudo-buttons with semantic `<button>` elements, add `aria-label` when appropriate, and ensure keyboard focus states (`:focus-visible`) are implemented.
