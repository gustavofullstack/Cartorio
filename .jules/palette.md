## 2026-07-02 - Improved accessibility in Swagger UI HTML template
**Learning:** Adding standard HTML5 elements (`header`, `nav`) instead of generic `div`s in Swagger templates improves accessibility via screen readers (semantic layout and `aria-label`). Providing a `focus-visible` class is key for keyboard navigation in custom elements injected into Swagger UI. Keep in mind that templates in python files have to use double brackets `{{` for CSS to escape formatting.
**Action:** Always prefer semantic HTML tags over generic `div` tags in embedded templates and ensure interactive elements have a `focus-visible` style so keyboard users can navigate clearly.
## 2026-07-04 - Fixed pytest-asyncio and app_env Literal issues
**Learning:** Adding new environments to settings validation might trigger a pydantic LiteralValidationError during tests if the new environment ('testing') is not whitelisted. Furthermore, when  shows warnings/errors, ensure  is installed.
**Action:** When troubleshooting failing test pipelines with Pydantic Settings, double check environment Literal enumerations. Verify missing dependencies like pytest-asyncio when resolving test discovery errors.
## 2026-07-04 - Fixed test config issues
**Learning:** Adding new environments to settings validation might trigger a pydantic LiteralValidationError during tests if the new environment is not whitelisted.
**Action:** When troubleshooting failing test pipelines with Pydantic Settings, double check environment Literal enumerations.
