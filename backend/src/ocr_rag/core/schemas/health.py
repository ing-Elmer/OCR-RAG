"""DTOs del endpoint de salud."""

from ocr_rag.core.schemas.base import CamelModel


class HealthResponse(CamelModel):
    """Estado de salud de la API y de la base de datos."""

    status: str
    database: str
    version: str
