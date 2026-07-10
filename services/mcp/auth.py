"""Phase 38 — MCP local-token auth guard.

When SCOTCH_MCP_TOKEN is set in the environment, every tool call that mutates
state is gated by a token check.  The token is passed as a parameter named
`_token` in the tool call (Claude Desktop / Cursor will forward it from their
MCP config's `env` block).

Usage (in server.py):
    from auth import require_token
    require_token(token)

Claude Desktop config (mcp_servers block in claude_desktop_config.json):
    {
      "scotch": {
        "command": "python",
        "args": ["/path/to/services/mcp/server.py"],
        "env": {
          "SCOTCH_MCP_TOKEN": "your-local-secret"
        }
      }
    }

If SCOTCH_MCP_TOKEN is not set, the guard is a no-op (local trust model).
"""

from __future__ import annotations

import os

_REQUIRED_TOKEN: str | None = os.environ.get("SCOTCH_MCP_TOKEN", "").strip() or None


def require_token(provided: str | None = None) -> None:
    """Raise ValueError if the provided token does not match the required token.

    No-op when SCOTCH_MCP_TOKEN is not configured (local trust mode).
    """
    if _REQUIRED_TOKEN is None:
        return
    if not provided or provided.strip() != _REQUIRED_TOKEN:
        raise ValueError(
            "MCP auth failed — SCOTCH_MCP_TOKEN mismatch. "
            "Set SCOTCH_MCP_TOKEN in both the server env and your MCP client config."
        )


def is_auth_required() -> bool:
    return _REQUIRED_TOKEN is not None
