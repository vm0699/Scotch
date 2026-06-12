from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import generate, health, projects
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Scotch API",
        description="AI-native architecture design platform — text-to-design for architecture.",
        version=settings.version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(generate.router)
    return app


app = create_app()
