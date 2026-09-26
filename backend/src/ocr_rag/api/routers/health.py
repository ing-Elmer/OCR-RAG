"""Router de salud."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ocr_rag.api.dependencies import get_health_service
from ocr_rag.api.responses import ApiResponse
from ocr_rag.application.services.health_service import HealthService
from ocr_rag.core.schemas.health import HealthResponse

# Router público: lo consultan balanceadores/orquestadores (Railway) sin token.
router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthResponse])
async def obtener_salud(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> ApiResponse[HealthResponse]:
    """Devuelve el estado de la API y de la conexión principal a la base."""
    estado = await service.obtener_estado()
    return ApiResponse[HealthResponse].ok("El servicio está operativo", estado)
