"""Interfaces (`Protocol`) de los clientes de servicios externos (OCR, embeddings)."""

from typing import Protocol


class OcrClient(Protocol):
    """Extrae texto de un documento mediante OCR."""

    async def extraer_texto(self, contenido: bytes, idioma: str) -> str:
        """Devuelve el texto reconocido en el contenido del documento."""
        ...


class EmbeddingClient(Protocol):
    """Genera embeddings vectoriales de texto para búsqueda semántica (`pgvector`)."""

    async def generar_embedding(self, texto: str) -> list[float]:
        """Devuelve el vector de embedding del texto dado."""
        ...
