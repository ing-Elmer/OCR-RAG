"""Service de documentos: carga, listado y detalle."""

import hashlib
import logging

from ocr_rag.application.background import TaskEnqueuer
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.core.repositories import DocumentoRepository
from ocr_rag.core.schemas.documento import DocumentoResponse

logger = logging.getLogger(__name__)


class DocumentoService:
    """Carga documentos, encola su procesamiento y resuelve su listado/detalle."""

    def __init__(
        self,
        repositorio: DocumentoRepository,
        validador: DocumentoValidator,
        procesador: ProcesamientoDocumentoService,
        cola: TaskEnqueuer,
    ) -> None:
        self._repositorio = repositorio
        self._validador = validador
        self._procesador = procesador
        self._cola = cola

    async def cargar(
        self,
        nombre_archivo: str,
        tipo_contenido: str,
        contenido: bytes,
        idioma: str | None,
        creado_por_id: int,
    ) -> DocumentoResponse:
        """Valida, guarda el documento (estado `pendiente`) y encola su procesamiento OCR."""
        documento = await self._guardar(
            nombre_archivo, tipo_contenido, contenido, idioma, creado_por_id, fuente_url=None
        )
        await self._cola.encolar(lambda: self._procesador.procesar(documento.id))
        return documento

    async def cargar_de_fuente(
        self,
        nombre_archivo: str,
        tipo_contenido: str,
        contenido: bytes,
        idioma: str | None,
        creado_por_id: int,
        fuente_url: str,
    ) -> DocumentoResponse:
        """Como `cargar`, pero para un documento ya obtenido de una fuente externa (carga
        masiva del corpus normativo, `cli cargar-corpus`).

        No encola el procesamiento: el CLI no tiene worker en background, así que el caller debe
        llamar a `procesar_ahora` directamente, en el mismo proceso.
        """
        return await self._guardar(
            nombre_archivo, tipo_contenido, contenido, idioma, creado_por_id, fuente_url
        )

    def validar_carga(
        self, nombre_archivo: str, tipo_contenido: str, tamano_bytes: int, idioma: str | None
    ) -> str:
        """Valida los datos de un archivo a cargar, sin persistir nada.

        Delega en el validador; lo usa `cli cargar-corpus --dry-run` para informar si una
        fuente sería válida sin escribir en la base. Devuelve el idioma normalizado.
        """
        return self._validador.validar_carga(nombre_archivo, tipo_contenido, tamano_bytes, idioma)

    async def buscar_por_sha256(self, sha256: str) -> DocumentoResponse | None:
        """Devuelve el documento ya cargado con ese `sha256`, o `None` si no existe.

        Lo usa `cli cargar-corpus` para no cargar dos veces el mismo contenido.
        """
        documento_id = await self._repositorio.obtener_id_por_sha256(sha256)
        if documento_id is None:
            return None
        return await self._repositorio.obtener(documento_id)

    async def procesar_ahora(self, documento_id: int) -> None:
        """Ejecuta el procesamiento OCR + embeddings de `documento_id` en el proceso actual, sin
        pasar por la cola de tareas en background. Lo usa `cli cargar-corpus`.
        """
        await self._procesador.procesar(documento_id)

    async def listar(self, limite: int, offset: int) -> tuple[list[DocumentoResponse], int]:
        """Lista los documentos paginados (más nuevo primero) y el total sin paginar."""
        return await self._repositorio.listar(limite, offset)

    async def obtener(self, documento_id: int) -> DocumentoResponse:
        """Devuelve el detalle de un documento. Lanza `NotFoundError` si no existe."""
        return await self._validador.validar_existente(documento_id)

    async def _guardar(
        self,
        nombre_archivo: str,
        tipo_contenido: str,
        contenido: bytes,
        idioma: str | None,
        creado_por_id: int,
        fuente_url: str | None,
    ) -> DocumentoResponse:
        """Valida y guarda el documento (estado `pendiente`) con su archivo original.

        Compartido por `cargar` (API, encola su procesamiento) y `cargar_de_fuente` (CLI,
        procesa en el mismo proceso), para no duplicar la validación ni el alta.
        """
        idioma_normalizado = self._validador.validar_carga(
            nombre_archivo, tipo_contenido, len(contenido), idioma
        )
        sha256 = hashlib.sha256(contenido).hexdigest()
        documento_id = await self._repositorio.crear(
            nombre_archivo=nombre_archivo,
            tipo_contenido=tipo_contenido,
            tamano_bytes=len(contenido),
            idioma=idioma_normalizado,
            creado_por_id=creado_por_id,
            contenido=contenido,
            sha256=sha256,
            fuente_url=fuente_url,
        )
        documento = await self._repositorio.obtener(documento_id)
        if documento is None:
            raise RuntimeError(f"El documento {documento_id} recién creado no se encontró")
        return documento
