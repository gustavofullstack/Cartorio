## 2024-03-20 - Focus Visible Outline Override
**Learning:** When resetting outline to none for hover and focus states, always provide a distinct focus-visible override to preserve accessibility.
**Action:** Use outline: none for :focus/:hover combined state and explicitly add an outline for :focus-visible.
