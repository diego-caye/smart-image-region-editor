from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.http.controllers import images_controller, operations_controller, static_files_controller
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.engine import init_db, make_engine


def create_app() -> FastAPI:
    settings = get_settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    init_db(make_engine(settings))

    app = FastAPI(title="Smart Image Region Editor API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(images_controller.router)
    app.include_router(operations_controller.router)
    app.include_router(static_files_controller.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
