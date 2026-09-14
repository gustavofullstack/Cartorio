## 2024-05-20 - Adding focus-visible
**Learning:** Found that the app uses static HTML templates (like `backend/app/static/dashboard.html`) without proper focus-visible styles on buttons for keyboard navigation.
**Action:** Adding `:focus-visible` to interactive elements like buttons allows keyboard users to clearly see which element has focus, while mouse users don't get unnecessary focus rings.
