# Auth Strategy — Scotch (Phase 18.1)

Scotch starts local-first: a single `"local-user"` owns all projects.
This document defines the upgrade path to multi-user cloud auth without
touching routes or store calls — the auth seam (`get_current_user_id`)
absorbs the complexity.

---

## Current state (Phase 18)

```
Request → route → get_current_user_id() → "local-user"
                                         ↓
                               store.get_project(id, user_id="local-user")
```

All routes use `Depends(get_current_user_id)` and thread `user_id` into
every store call. The dependency returns `"local-user"` unconditionally —
no tokens, no sessions, no config needed.

---

## Upgrade path: Google OAuth 2.0 (PKCE)

### Why Google OAuth + PKCE
- PKCE (Proof Key for Code Exchange) is the current secure flow for SPAs —
  no client secret exposed in browser code.
- Google Identity Services (`accounts.google.com`) handles token issuance.
- The Scotch backend only validates JWTs; it never stores passwords.

### Auth flow

```
Browser                   Google                    Scotch API
  │                          │                           │
  │── /auth/login ──────────►│                           │
  │   (PKCE code_challenge)  │                           │
  │◄── authorization_code ───│                           │
  │                          │                           │
  │── POST /auth/callback ──────────────────────────────►│
  │   (code + code_verifier)                             │
  │                          │◄── token exchange ────────│
  │                          │──► id_token + access_token►│
  │◄── Set-Cookie: session ──────────────────────────────│
  │    (HttpOnly, SameSite=Strict, Secure)               │
  │                                                      │
  │── GET /projects (Authorization: Bearer <jwt>) ──────►│
  │◄── 200 [ProjectSummary] ─────────────────────────────│
```

### JWT structure

```json
{
  "sub": "google-oauth2|117304...",   // stable Google user id → user_id
  "email": "user@example.com",
  "name": "Vignesh M",
  "iat": 1718000000,
  "exp": 1718003600,
  "iss": "https://accounts.google.com"
}
```

`sub` is the `user_id` threaded into every store call. It is stable across
email changes and Google account renames.

### Backend implementation (Phase 18+ / post-Phase 20)

```python
# core/auth/context.py — cloud body (replace the local-user return)
from fastapi import Header, HTTPException
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as grequests

async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ")
    try:
        info = google_id_token.verify_oauth2_token(
            token, grequests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return info["sub"]
```

No route changes required — they already call `Depends(get_current_user_id)`.

---

## Session / JWT handling

| Concern | Approach |
|---|---|
| Token storage (browser) | `HttpOnly` cookie (not localStorage — prevents XSS theft) |
| Token lifetime | 1-hour access token; 30-day refresh token |
| Token refresh | Silent refresh via `/auth/refresh` endpoint |
| CSRF protection | `SameSite=Strict` cookie + double-submit cookie pattern |
| Logout | DELETE `/auth/session`; revoke refresh token at Google |

---

## Project ownership

```
user_id (from JWT sub)
  └── projects/{project_id}/project.json
  └── projects/{project_id}/exports/
```

Every store method already requires `(project_id, user_id)`. A user can
only access projects where the stored `user_id` matches their JWT `sub`.
No cross-user access unless explicit sharing is added (future).

### Future: team ownership

```
team_id  →  team_members[user_id → role]
         →  team_projects[project_id]
```

Routes would check `user_id ∈ team_members` before allowing access to
team-owned projects. The store interface accommodates this via an optional
`owner_id` parameter on `get_project` / `update_project`.

---

## Local ↔ cloud migration

A user's local projects live under `"local-user"`. On first cloud login:
1. Backend generates a migration token scoped to the local session.
2. Frontend calls `POST /auth/migrate` with the token and new `user_id`.
3. Backend moves all `local-user` project files to the new `user_id` namespace.
4. Old `local-user` data is purged after migration confirmation.

---

## Security checklist

- [ ] Validate JWT signature against Google's public keys (JWKS endpoint)
- [ ] Verify `aud` (audience) matches `SCOTCH_GOOGLE_CLIENT_ID`
- [ ] Verify `iss` is `"https://accounts.google.com"`
- [ ] Check token `exp` (never trust expired tokens)
- [ ] Rate-limit `/auth/callback` to prevent token stuffing
- [ ] Rotate `SCOTCH_JWT_SECRET` if used for first-party JWTs
- [ ] HTTPS everywhere in production (Scotch API + frontend)

---

## Environment variables (Phase 18+)

| Variable | Description | Example |
|---|---|---|
| `SCOTCH_GOOGLE_CLIENT_ID` | OAuth 2.0 client ID from Google Cloud Console | `123456.apps.googleusercontent.com` |
| `SCOTCH_GOOGLE_CLIENT_SECRET` | Client secret (never in frontend) | `GOCSPX-...` |
| `SCOTCH_JWT_SECRET` | Secret for signing first-party JWTs (if used) | random 256-bit hex |
| `SCOTCH_AUTH_CALLBACK_URL` | Redirect URI registered in Google Console | `https://app.scotch.ai/auth/callback` |

*Generated by Scotch — Phase 18.1*
