from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cameras, exports, generate, health, intelligence, integrations, projects, versions
from app.api.routes import settings as settings_routes
from app.config import get_settings


def create_app() -> FastAPI:
    cfg = get_settings()
    app = FastAPI(
        title="Scotch API",
        description="AI-native architecture design platform — text-to-design for architecture.",
        version=cfg.version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(generate.router)
    app.include_router(exports.router)
    app.include_router(intelligence.router)
    app.include_router(cameras.router)
    app.include_router(integrations.router)
    app.include_router(settings_routes.router)
    app.include_router(versions.router)
    return app


app = create_app()
