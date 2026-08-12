## 2024-08-12 - Fix focus-visible outline accessibility
**Learning:** When applying `outline: none;` to combined `:hover, :focus-visible` states to prevent focus rings on mouse clicks in the dashboards, keyboard navigation accessibility is compromised because focus rings are lost.
**Action:** Always append a separate, distinct rule exclusively for `:focus-visible` (e.g., `outline: 2px solid var(--brand); outline-offset: -2px;`) to ensure keyboard users retain visual focus indicators.
