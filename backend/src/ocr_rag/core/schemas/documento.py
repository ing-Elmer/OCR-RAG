"""DTOs de documentos y consultas (RAG), y tipos internos compartidos entre `application` e
`infrastructure` para el pipeline de OCR + embeddings.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from ocr_rag.core.schemas.base import CamelModel

EstadoDocumento = Literal["pendiente", "procesando", "procesado", "error"]

TipoDocumento = Literal["normativa", "embarque", "aduanero", "contrato", "otro"]

# Valores válidos de `TipoDocumento`, en el mismo orden que el `CHECK` de
# `db/007_alter_documento_tipo_norma.sql`. Fuente única para validadores y clasificador.
TIPOS_DOCUMENTO: tuple[TipoDocumento, ...] = (
    "normativa",
    "embarque",
    "aduanero",
    "contrato",
    "otro",
)

TOP_K_POR_DEFECTO = 8
TOP_K_MAXIMO = 20


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
    tipo_documento: TipoDocumento
    norma: str | None = None


class DocumentoActualizacionRequest(CamelModel):
    """Body de `PATCH /api/documentos/{id}`.

    Distingue un campo ausente (no tocar esa columna) de uno presente con valor `null`
    (limpiarla), mediante `model_fields_set`: por eso ambos campos son opcionales sin bastar con
    mirar si su valor es `None`. `tipoDocumento` no admite `null` explícito porque la columna es
    `NOT NULL` en la base.
    """

    tipo_documento: TipoDocumento | None = None
    norma: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def _validar_cuerpo_no_vacio(self) -> "DocumentoActualizacionRequest":
        campos_provistos = self.model_fields_set
        if not campos_provistos:
            raise ValueError("Debe enviar al menos un campo para actualizar")
        if "tipo_documento" in campos_provistos and self.tipo_documento is None:
            raise ValueError("tipoDocumento no puede ser nulo")
        return self


class ConsultaRequest(CamelModel):
    """Body de `POST /api/consultas`."""

    pregunta: str = Field(min_length=3, max_length=2000)
    documento_ids: list[int] | None = None
    tipos_documento: list[TipoDocumento] | None = None
    top_k: int = Field(default=TOP_K_POR_DEFECTO, ge=1, le=TOP_K_MAXIMO)


class FuenteConsulta(CamelModel):
    """Chunk usado como fuente de una respuesta de consulta."""

    documento_id: int
    nombre_archivo: str
    orden: int
    pagina: int | None
    fragmento: str
    similitud: float
    tipo_documento: TipoDocumento
    fuente_url: str | None = None
    norma: str | None = None
    articulo: str | None = None


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
    articulo: str | None = None


@dataclass(frozen=True, slots=True)
class ChunkParaGuardar:
    """Fragmento de texto con su embedding ya calculado, listo para persistir."""

    orden: int
    contenido: str
    pagina: int | None
    embedding: list[float]
    articulo: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentoParaProcesar:
    """Datos que necesita el worker de procesamiento, tomados en forma exclusiva.

    `version_procesamiento` es la versión vigente al momento de la toma: el worker debe usarla
    para condicionar el guardado del resultado (o el marcado de error), así un reprocesamiento
    más nuevo (encolado mientras este todavía corría) nunca se pisa con uno viejo.
    `clasificacion_pendiente` indica si la carga no trajo `tipoDocumento` y todavía nadie la
    clasificó (ni el worker en un intento anterior, ni una edición manual).
    """

    id: int
    idioma: str
    tipo_contenido: str
    contenido: bytes
    tipo_documento: TipoDocumento
    version_procesamiento: int
    clasificacion_pendiente: bool
    norma: str | None = None


@dataclass(frozen=True, slots=True)
class FragmentoContexto:
    """Fragmento de contexto que se pasa al `ChatClient` para responder una consulta.

    Lleva los metadatos necesarios para armar el encabezado que ve el modelo (norma, artículo,
    página); `numero` es la posición del fragmento en `fuentes` (1-based), la misma que el
    modelo debe citar entre corchetes (p. ej. `[1]`).
    """

    numero: int
    contenido: str
    nombre_archivo: str
    norma: str | None = None
    articulo: str | None = None
    pagina: int | None = None


@dataclass(frozen=True, slots=True)
class ChunkSimilar:
    """Resultado de una búsqueda (vectorial o léxica): un chunk y su similitud con la pregunta.

    `similitud` es siempre la similitud coseno del embedding del chunk contra el de la pregunta,
    calculada en SQL en ambas búsquedas (vectorial y léxica): así un chunk que entra solo por la
    búsqueda de texto completo ya trae una similitud real, sin tener que estimarla en Python.
    """

    documento_id: int
    nombre_archivo: str
    orden: int
    pagina: int | None
    contenido: str
    similitud: float
    fuente_url: str | None = None
    norma: str | None = None
    articulo: str | None = None
    tipo_documento: TipoDocumento = "otro"
