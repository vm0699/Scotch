"""FastAPI dependency providers — Phase 37."""
from app.api.dependencies.auth import get_current_user_id

__all__ = ["get_current_user_id"]
