"""Interfaces (`Protocol`) de los clientes de servicios externos (OCR, embeddings, chat,
descarga de archivos remotos).
"""

from typing import Protocol

from ocr_rag.core.schemas.corpus import ArchivoDescargado
from ocr_rag.core.schemas.documento import PaginaExtraida


class OcrClient(Protocol):
    """Extrae texto de una imagen mediante OCR."""

    async def extraer_texto(self, contenido: bytes, idioma: str) -> str:
        """Devuelve el texto reconocido en el contenido de la imagen."""
        ...


class EmbeddingClient(Protocol):
    """Genera embeddings vectoriales de texto para búsqueda semántica (`pgvector`)."""

    async def generar_embeddings(self, textos: list[str]) -> list[list[float]]:
        """Devuelve, en el mismo orden que `textos`, el vector de embedding de cada uno."""
        ...


class ChatClient(Protocol):
    """Genera una respuesta en lenguaje natural a partir de una pregunta y sus contextos."""

    async def responder(self, pregunta: str, contextos: list[str]) -> str:
        """Responde `pregunta` usando únicamente la información de `contextos`."""
        ...


class ExtractorTexto(Protocol):
    """Extrae el texto de un documento (PDF o imagen), combinando texto nativo y OCR."""

    async def extraer(
        self, contenido: bytes, tipo_contenido: str, idioma: str
    ) -> list[PaginaExtraida]:
        """Devuelve el texto de cada página del documento, en orden."""
        ...


class DescargadorHttp(Protocol):
    """Descarga un archivo remoto por HTTPS, con límites de seguridad.

    Implementación de infraestructura para el comando de CLI `cargar-corpus`; nunca se usa
    desde un endpoint HTTP.
    """

    async def descargar(self, url: str, limite_bytes: int) -> ArchivoDescargado:
        """Descarga `url`.

        Lanza `DescargaInvalidaError` si `url` (o alguna redirección) no es https, si el
        contenido supera `limite_bytes`, o si no es un PDF válido (por `content-type` o firma).
        """
        ...
