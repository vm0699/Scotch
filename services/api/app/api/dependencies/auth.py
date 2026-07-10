"""Authentication dependency — Phase 37.

In local-first mode:  always returns "local-user" (no token needed).
In cloud mode (future): reads a Bearer JWT from the Authorization header,
verifies it, and returns the claim's sub (user id).

Swapping the implementation here is the ONLY change needed to move the
entire API from local to cloud auth — no route files need changing.

Usage in routes:
    from app.api.dependencies import get_current_user_id
    @router.get("/something")
    def handler(user_id: str = Depends(get_current_user_id)):
        ...
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException

from app.core.storage.base import LOCAL_USER_ID

def get_current_user_id(
    authorization: str | None = Header(default=None, include_in_schema=False),
) -> str:
    """Return the authenticated user id.

    local mode — returns LOCAL_USER_ID ("local-user") unconditionally.
    cloud mode — parses the Bearer token (stub; raises 401 until implemented).
    """
    # Read at call time so monkeypatch/importlib.reload in tests don't leave stale state.
    if os.environ.get("SCOTCH_AUTH_MODE", "local") == "local":
        return LOCAL_USER_ID

    # Cloud mode (stub — will be replaced with real JWT validation in cloud phase)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or not Bearer token.",
        )
    # Placeholder: accept any non-empty token and return its value as user id.
    # Real implementation: decode + verify JWT, extract sub claim.
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty Bearer token.")
    return f"cloud-user-{token[:16]}"
