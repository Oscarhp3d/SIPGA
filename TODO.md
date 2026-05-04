# SIPRA Frontend Auth Refactor TODO
Status: [ ] In Progress

## Steps:
1. [x] Create frontend/js/login.js - Login function for POST /api/v1/auth/token, token storage, getAuthHeaders().
2. [x] Edit frontend/index.html - 
   - Add /api/v1 prefix to all fetches (/ → /api/v1/, /usuarios/ → /api/v1/usuarios/).
   - Wrap fetches with getAuthHeaders() from login.js.
   - Add login form HTML + onclick=loginUser().
   - Add <script src=\"js/login.js\">.
   - Fixed JS syntax errors, added subirEvidencia impl.
3. [ ] Test: Open index.html, login, check token/localStorage, protected calls.
4. [ ] [ ] Update TODO as steps complete.
5. [ ] attempt_completion.

Next: Implement step 1.

