from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import boq, cameras, changes, chat, compliance, details, exports, feasibility, fixtures, generate, health, intelligence, integrations, mep, profile, program, projects, references, render, review, sync, system, versions
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
    app.include_router(program.router)
    app.include_router(render.router)
    app.include_router(chat.router)
    app.include_router(sync.router)
    app.include_router(compliance.router)
    app.include_router(mep.router)
    app.include_router(details.router)
    app.include_router(boq.router)
    app.include_router(changes.router)
    app.include_router(profile.router)
    app.include_router(references.router)
    app.include_router(feasibility.router)
    app.include_router(review.router)
    app.include_router(fixtures.router)
    app.include_router(system.router)
    return app


app = create_app()
