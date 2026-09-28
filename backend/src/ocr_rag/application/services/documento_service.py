"""Service de documentos: carga, listado y detalle."""

import hashlib
import logging

from ocr_rag.application.background import Tarea, TaskEnqueuer
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.core.exceptions import NotFoundError
from ocr_rag.core.repositories import DocumentoRepository
from ocr_rag.core.schemas.documento import (
    DocumentoActualizacionRequest,
    DocumentoResponse,
    TipoDocumento,
)

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
        tipo_documento: TipoDocumento | None = None,
    ) -> DocumentoResponse:
        """Valida, guarda el documento (estado `pendiente`) y encola su procesamiento OCR.

        Si `tipo_documento` es `None` (la carga no lo indicó), el worker lo clasifica
        automáticamente con el modelo de chat, después de extraer el texto.
        """
        documento = await self._guardar(
            nombre_archivo,
            tipo_contenido,
            contenido,
            idioma,
            creado_por_id,
            fuente_url=None,
            tipo_documento=tipo_documento,
            norma=None,
        )
        await self._cola.encolar(self._tarea_de_procesamiento(documento.id))
        return documento

    async def cargar_de_fuente(
        self,
        nombre_archivo: str,
        tipo_contenido: str,
        contenido: bytes,
        idioma: str | None,
        creado_por_id: int,
        fuente_url: str,
        tipo_documento: TipoDocumento,
        norma: str | None = None,
    ) -> DocumentoResponse:
        """Como `cargar`, pero para un documento ya obtenido de una fuente externa (carga
        masiva del corpus normativo, `cli cargar-corpus`), que siempre trae su `tipo_documento`
        (y, opcionalmente, su `norma`) desde el manifiesto.

        No encola el procesamiento: el CLI no tiene worker en background, así que el caller debe
        llamar a `procesar_ahora` directamente, en el mismo proceso.
        """
        return await self._guardar(
            nombre_archivo,
            tipo_contenido,
            contenido,
            idioma,
            creado_por_id,
            fuente_url,
            tipo_documento=tipo_documento,
            norma=norma,
        )

    async def actualizar(
        self, documento_id: int, cambios: DocumentoActualizacionRequest
    ) -> DocumentoResponse:
        """Actualiza el tipo y/o la norma de un documento existente.

        Si `tipoDocumento` cambia a o desde `"normativa"`, reencola su procesamiento (en una
        fase posterior el chunking va a depender del tipo); esa edición manual siempre limpia
        `clasificacion_pendiente`, aunque no cruce la frontera de `"normativa"`. Lanza
        `NotFoundError` si el documento no existe.
        """
        documento_actual = await self._validador.validar_existente(documento_id)

        campos_provistos = cambios.model_fields_set
        tipo_nuevo = cambios.tipo_documento if "tipo_documento" in campos_provistos else None
        actualizar_norma = "norma" in campos_provistos
        reencolar = tipo_nuevo is not None and _cambia_a_o_desde_normativa(
            documento_actual.tipo_documento, tipo_nuevo
        )

        existia = await self._repositorio.actualizar(
            documento_id,
            tipo_nuevo,
            cambios.norma,
            actualizar_norma=actualizar_norma,
            reencolar=reencolar,
        )
        if not existia:
            raise NotFoundError(f"No se encontró el documento {documento_id}")

        documento_actualizado = await self._repositorio.obtener(documento_id)
        if documento_actualizado is None:
            raise RuntimeError(f"El documento {documento_id} actualizado no se encontró")

        if reencolar:
            await self._cola.encolar(self._tarea_de_procesamiento(documento_id))

        return documento_actualizado

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

    async def procesar_ahora(self, documento_id: int) -> bool:
        """Ejecuta el procesamiento OCR + embeddings de `documento_id` en el proceso actual, sin
        pasar por la cola de tareas en background. Lo usa `cli cargar-corpus`.

        Devuelve `False` si no lo pudo tomar (otro proceso ya lo tenía); `True` si lo tomó.
        """
        return await self._procesador.procesar(documento_id)

    async def reprocesar_ahora(self, documento_id: int) -> bool:
        """Como `procesar_ahora`, pero primero incrementa `version_procesamiento`.

        Así descarta cualquier procesamiento en vuelo que todavía sostenga una versión anterior,
        aunque este documento esté `procesando` y la propia toma termine "omitida". Lo usa
        `cli reprocesar`, que puede apuntar a un documento por id sin importar su estado actual.
        """
        await self._repositorio.incrementar_version(documento_id)
        return await self._procesador.procesar(documento_id)

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
        tipo_documento: TipoDocumento | None,
        norma: str | None,
    ) -> DocumentoResponse:
        """Valida y guarda el documento (estado `pendiente`) con su archivo original.

        Compartido por `cargar` (API, encola su procesamiento) y `cargar_de_fuente` (CLI,
        procesa en el mismo proceso), para no duplicar la validación ni el alta. `tipo_documento`
        en `None` se guarda como `"otro"` (la columna es `NOT NULL`); el worker lo reemplaza por
        el que resulte de clasificar el documento.
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
            tipo_documento=tipo_documento or "otro",
            norma=norma,
            clasificacion_pendiente=tipo_documento is None,
        )
        documento = await self._repositorio.obtener(documento_id)
        if documento is None:
            raise RuntimeError(f"El documento {documento_id} recién creado no se encontró")
        return documento

    def _tarea_de_procesamiento(self, documento_id: int) -> Tarea:
        """Arma la tarea de procesamiento de `documento_id`, ligado en el momento de crearla
        (evita el late binding de un closure) y descartando el `bool` que devuelve `procesar`
        (la cola de tareas no lo necesita).
        """

        async def _tarea() -> None:
            await self._procesador.procesar(documento_id)

        return _tarea


def _cambia_a_o_desde_normativa(anterior: TipoDocumento, nuevo: TipoDocumento) -> bool:
    """Indica si `tipo_documento` pasó a ser `"normativa"` o dejó de serlo."""
    return (anterior == "normativa") != (nuevo == "normativa")
