"""Point d'entrée FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from geodashboard_api.config import get_settings
from geodashboard_api.middleware import security_headers
from geodashboard_api.routers.diagnostics import router as diagnostics_router
from geodashboard_api.routers.expert import router as expert_router
from geodashboard_api.routers.health import router as health_router
from geodashboard_api.routers.layers import router as layers_router
from geodashboard_api.routers.restitution import router as restitution_router
from geodashboard_api.routers.territories import router as territories_router


def create_app() -> FastAPI:
    """Construit l'application et ses frontières de sécurité."""
    settings = get_settings()
    app = FastAPI(
        title="GeoDashboard API",
        summary="Moteur de diagnostic et de scénarios territoriaux",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.api_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Session-ID"],
    )
    app.middleware("http")(security_headers)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(diagnostics_router, prefix="/api/v1")
    app.include_router(expert_router, prefix="/api/v1")
    app.include_router(restitution_router, prefix="/api/v1")
    app.include_router(layers_router, prefix="/api/v1")
    app.include_router(territories_router, prefix="/api/v1")
    return app


app = create_app()
