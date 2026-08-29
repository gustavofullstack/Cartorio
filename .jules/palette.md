## 2025-02-12 - AI Data Extractor Button States & Screen Reader Support
**Learning:** In a highly interactive simulator interface, dynamically populated results (like AI extractions and PII pipelines) risk being missed by screen readers. Furthermore, simulated API delays without visual feedback confuse users clicking action buttons.
**Action:** Added `aria-live="polite"` to dynamic result containers and wrapped async logic in `try...finally` to ensure buttons enter a disabled state with visual loading feedback and reliably restore functionality regardless of execution outcome.
