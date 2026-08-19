"""État de fonctionnement sans exposition de secrets."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Réponse stable utilisée par l'orchestrateur et le frontend."""

    status: Literal["ok"] = "ok"
    service: str = "geodashboard-api"
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Confirme que le processus HTTP répond."""
    return HealthResponse()
