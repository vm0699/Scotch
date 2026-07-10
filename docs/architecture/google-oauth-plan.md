# Scotch — Google OAuth 2.0 + PKCE Plan

*Phase 37 · Last updated 2026-06-22*

## Goals

1. Sign in with Google without storing passwords.
2. Each user owns their own projects; `user_id` in all storage paths flips from `"local-user"` to the real Google sub.
3. Local-first mode stays fully functional with no token required.
4. A single dep swap (`get_current_user_id`) moves the entire API from local to cloud auth.

---

## Environment variables

| Variable | Required for | Description |
|---|---|---|
| `SCOTCH_AUTH_MODE` | cloud | `"local"` (default) or `"cloud"` |
| `GOOGLE_CLIENT_ID` | cloud | OAuth 2.0 client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | cloud | OAuth 2.0 client secret |
| `SCOTCH_JWT_SECRET` | cloud | HS256 signing secret for Scotch session JWT |
| `SCOTCH_JWT_TTL_HOURS` | cloud | JWT time-to-live (default `168` = 7 days) |
| `SCOTCH_FRONTEND_URL` | cloud | Allowed OAuth redirect origin (e.g. `https://app.scotch.ai`) |

---

## Flow overview (PKCE)

```
Browser                         FastAPI                      Google
  │                                │                            │
  │  GET /auth/google/login        │                            │
  │───────────────────────────────►│                            │
  │                                │  generate code_verifier    │
  │  302 → accounts.google.com     │  + code_challenge          │
  │◄───────────────────────────────│                            │
  │                                │                            │
  │  User logs in at Google        │                            │
  │───────────────────────────────────────────────────────────►│
  │◄─────────────────────────────────────── code ─────────────│
  │                                │                            │
  │  GET /auth/google/callback?code=…                          │
  │───────────────────────────────►│                            │
  │                                │  POST /token (code + verifier)
  │                                │───────────────────────────►│
  │                                │◄────────── id_token ──────│
  │                                │  verify id_token           │
  │                                │  upsert user row           │
  │                                │  mint Scotch JWT           │
  │  Set-Cookie: scotch_session    │                            │
  │◄───────────────────────────────│                            │
```

---

## Routes (to add when cloud mode activates)

```
GET  /auth/google/login           → redirect to Google consent
GET  /auth/google/callback        → exchange code, set session cookie, redirect to dashboard
GET  /auth/me                     → { user_id, email, display_name, account_mode }
POST /auth/logout                 → clear session cookie
```

All implemented in `app/api/routes/auth.py` (to be created in cloud phase).

---

## JWT / session strategy

Scotch issues its own short-lived JWT after Google callback — avoids sending Google tokens to the frontend.

**Payload:**
```json
{
  "sub": "google:117…",         // Google user ID, stable sub
  "email": "user@example.com",
  "name": "Priya Sharma",
  "iat": 1735000000,
  "exp": 1735604800
}
```

**Storage:** `HttpOnly; SameSite=Lax; Secure` cookie named `scotch_session`.  
Alternatively: localStorage `scotch_token` for SPA + CORS mode (less secure).

**Verification in `get_current_user_id`:**
```python
import jwt
payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
return payload["sub"]          # "google:117…"
```

---

## User and project ownership

```
data/users/{google_sub}/projects/{project_id}/project.json
data/users/{google_sub}/profile.json
```

All `ProjectStore` methods already accept `user_id` — no schema change needed.  
`LocalProjectStore` paths already use `user_id` — works for both local and cloud user IDs.

---

## Local → Cloud migration

When a signed-in user wants to push local projects to the cloud:

1. `GET /auth/migrate-check` — list local `local-user` projects.
2. `POST /auth/migrate` — copy each project to `{google_sub}/…` in cloud storage.
3. Keep a `migration_log.json` sidecar so the op is idempotent.

This is a single-session, user-triggered operation — not an automatic background sync.

---

## Database strategy

See `docs/architecture/database-strategy.md` for the full Postgres schema.  
For the auth layer only:

```sql
CREATE TABLE users (
    id           TEXT PRIMARY KEY,   -- "google:117…"
    email        TEXT UNIQUE,
    display_name TEXT,
    created_at   TIMESTAMPTZ DEFAULT now(),
    last_login   TIMESTAMPTZ
);
```

---

## Security checklist

- [x] PKCE (no `response_type=token`; code flow only)
- [x] `state` parameter in OAuth request (CSRF protection)
- [x] `code_verifier` stored server-side per session (prevents intercept)
- [x] `HttpOnly; Secure` cookie (XSS-safe)
- [x] JWT TTL — 7 days; refresh on activity
- [x] Rate-limit `/auth/google/callback` (brute-force)
- [x] Validate `aud` claim in Google id_token matches `GOOGLE_CLIENT_ID`
- [ ] Token rotation on every request (future hardening)
- [ ] Revocation list for stolen tokens (future hardening)

---

## Implementation order (when cloud phase starts)

1. Add `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SCOTCH_JWT_SECRET` to `Config`.
2. `pip install google-auth PyJWT` — add to requirements.txt.
3. Implement `app/api/routes/auth.py` (login / callback / me / logout).
4. Swap `get_current_user_id` dep from stub to real JWT decode.
5. Update `CloudProjectStore` to use cloud bucket with `user_id` path.
6. Add `users` table migration.
7. Update Next.js frontend: sign-in button, session cookie handling, `/auth/me` call.
