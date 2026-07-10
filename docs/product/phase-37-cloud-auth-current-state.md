# Phase 37 — Cloud/Auth Prep: Current State Recon

*Inspected 2026-06-22 before implementation.*

## Objective

Prepare personalization + multi-user storage without breaking local-first mode.  
No live cloud deployment required — seams and docs must be ready for it.

## What already exists (from earlier phases)

| Area | File | Notes |
|---|---|---|
| `ProjectStore` ABC | `core/storage/base.py` | `user_id` param on every method — cloud-ready |
| `LocalProjectStore` | `core/storage/local_store.py` | Atomic writes, version sidecars, manifest |
| `CloudProjectStore` stub | `core/storage/cloud_store.py` | All methods raise `NotImplementedError` |
| Storage factory | `core/storage/factory.py` | `SCOTCH_STORAGE_BACKEND=local|cloud`; `@lru_cache` singleton |
| Auth seam | `LOCAL_USER_ID = "local-user"` in `base.py` | Used by all routes as hardcoded constant |
| Profile store | `core/profile/store.py` | `LocalUserProfileStore`, `get_profile_store()` |
| Profile model | `core/profile/models.py` | `UserProfile`, `ClientBrief` |
| Profile routes | `api/routes/profile.py` | `GET/PUT /profile`, `GET/PUT /profile/projects/{id}/brief` |
| SQLite index | `core/storage/sqlite_index.py` | `(user_id, updated_at DESC)` — cloud-index ready |

## Gaps that Phase 37 fills

1. **Injectable `get_current_user_id` dep** — routes hard-code `LOCAL_USER_ID` instead of calling a dependency. Moving to a dep allows Google OAuth to slot in by swapping the dep.
2. **Account-mode awareness** — `UserProfile` has no `account_mode` / `cloud_email` / `display_name` fields. Profile UI can't show sign-in state.
3. **Google OAuth plan** — documented plan for PKCE flow, JWT/session strategy, user/project ownership, migration path needed before any cloud work starts.
4. **Cloud-store interface tests** — no tests verify `LocalProjectStore` satisfies every `ProjectStore` abstract method, or that `CloudProjectStore` raises correctly.
5. **Account/profile UI** — no frontend panel shows sign-in status, local account indicator, or sign-in placeholder.

## Non-regressions verified

- All 946 tests pass with local-only mode.
- `LOCAL_USER_ID = "local-user"` keeps working after new dep is introduced.
- Cloud stub still raises `NotImplementedError` — no behaviour change.
