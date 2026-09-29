"""Service de salud del sistema."""

import logging

from ocr_rag.core.repositories import HealthRepository
from ocr_rag.core.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

_VERSION = "0.1.0"


class HealthService:
    """Resuelve el estado de salud de la API y de sus dependencias."""

    def __init__(self, repositorio: HealthRepository) -> None:
        self._repositorio = repositorio

    async def obtener_estado(self) -> HealthResponse:
        """Verifica la base de datos y arma la respuesta de salud."""
        base_ok = await self._repositorio.verificar_conexion()
        if not base_ok:
            logger.warning("La verificación de la conexión principal a la base falló")
        return HealthResponse(
            status="ok",
            database="ok" if base_ok else "error",
            version=_VERSION,
        )
