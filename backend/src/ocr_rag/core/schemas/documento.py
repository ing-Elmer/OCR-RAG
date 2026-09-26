"""DTOs de documentos y consultas (RAG), y tipos internos compartidos entre `application` e
`infrastructure` para el pipeline de OCR + embeddings.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import Field

from ocr_rag.core.schemas.base import CamelModel

EstadoDocumento = Literal["pendiente", "procesando", "procesado", "error"]


# =============================================================================================
# DTOs de la API (contrato con el frontend, en camelCase)
# =============================================================================================


class DocumentoResponse(CamelModel):
    """Documento cargado, tal como se expone por la API."""

    id: int
    nombre_archivo: str
    tipo_contenido: str
    tamano_bytes: int
    estado: EstadoDocumento
    idioma: str | None
    paginas: int | None
    cantidad_chunks: int
    error_detalle: str | None
    created_at: datetime
    fuente_url: str | None = None


class ConsultaRequest(CamelModel):
    """Body de `POST /api/consultas`."""

    pregunta: str = Field(min_length=3, max_length=2000)
    documento_ids: list[int] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class FuenteConsulta(CamelModel):
    """Chunk usado como fuente de una respuesta de consulta."""

    documento_id: int
    nombre_archivo: str
    orden: int
    pagina: int | None
    fragmento: str
    similitud: float
    fuente_url: str | None = None


class ConsultaResponse(CamelModel):
    """Respuesta de `POST /api/consultas`."""

    respuesta: str
    fuentes: list[FuenteConsulta]


# =============================================================================================
# Tipos internos del pipeline (no se exponen por la API): comparten `core` porque los produce
# `infrastructure` (extractor, repositorio) y los consume `application` (chunking, services).
# =============================================================================================


@dataclass(frozen=True, slots=True)
class PaginaExtraida:
    """Texto reconocido (nativo u OCR) de una página de un documento."""

    numero: int
    texto: str


@dataclass(frozen=True, slots=True)
class ChunkTexto:
    """Fragmento de texto resultante del chunking, antes de generarle el embedding."""

    orden: int
    contenido: str
    pagina: int | None


@dataclass(frozen=True, slots=True)
class ChunkParaGuardar:
    """Fragmento de texto con su embedding ya calculado, listo para persistir."""

    orden: int
    contenido: str
    pagina: int | None
    embedding: list[float]


@dataclass(frozen=True, slots=True)
class DocumentoParaProcesar:
    """Datos mínimos de un documento que necesita el worker de procesamiento."""

    id: int
    idioma: str
    tipo_contenido: str
    contenido: bytes


@dataclass(frozen=True, slots=True)
class ChunkSimilar:
    """Resultado de la búsqueda semántica: un chunk y su similitud con la pregunta."""

    documento_id: int
    nombre_archivo: str
    orden: int
    pagina: int | None
    contenido: str
    similitud: float
    fuente_url: str | None = None
