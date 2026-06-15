"""Auth context seam — Phase 18.1.

Today this dependency returns "local-user" unconditionally, preserving
existing local-first behaviour with zero config.

Cloud upgrade path (Phase 18+):
  Replace the body of get_current_user_id() with JWT decode from the
  `Authorization: Bearer <token>` header. The rest of the codebase
  (routes, store calls) needs no changes because they already receive
  `user_id` via Depends().

  async def get_current_user_id(
      authorization: str | None = Header(default=None),
  ) -> str:
      if not authorization or not authorization.startswith("Bearer "):
          raise HTTPException(status_code=401, detail="Missing credentials")
      token = authorization.removeprefix("Bearer ")
      payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
      return payload["sub"]          # Google OAuth subject = stable user id

Test override pattern:
  app.dependency_overrides[get_current_user_id] = lambda: "test-user-xyz"
  # All store calls now scope to "test-user-xyz" — no data leaks between users.
"""

LOCAL_USER_ID = "local-user"


async def get_current_user_id() -> str:
    """FastAPI dependency: return the active user_id for the current request.

    Phase 18 local mode: always "local-user".
    Cloud mode: decode from JWT (see module docstring).
    """
    return LOCAL_USER_ID
