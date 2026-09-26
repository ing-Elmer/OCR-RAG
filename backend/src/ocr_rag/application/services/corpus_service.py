"""Service de carga masiva del corpus normativo: comando de CLI `cargar-corpus`.

Descarga cada fuente del manifiesto, la valida con el mismo `DocumentoValidator` que usa la
carga por la API, la guarda y la procesa (OCR + embeddings) en el mismo proceso, porque el CLI
no tiene un worker en background.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Literal

from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.core.clients import DescargadorHttp
from ocr_rag.core.exceptions import DescargaInvalidaError, ValidationError
from ocr_rag.core.schemas.corpus import FuenteCorpus
from ocr_rag.core.settings import Settings

logger = logging.getLogger(__name__)

_BYTES_POR_MB = 1024 * 1024

EstadoCargaFuente = Literal["cargado", "omitido", "error"]


@dataclass(frozen=True, slots=True)
class ResultadoCargaFuente:
    """Resultado de intentar cargar una fuente del manifiesto de corpus."""

    fuente_id: str
    estado: EstadoCargaFuente
    documento_id: int | None
    detalle: str


class CorpusService:
    """Descarga, valida, carga y procesa cada fuente de un manifiesto de corpus normativo."""

    def __init__(
        self,
        documento_service: DocumentoService,
        descargador: DescargadorHttp,
        settings: Settings,
    ) -> None:
        self._documento_service = documento_service
        self._descargador = descargador
        self._settings = settings

    async def cargar_fuente(
        self, fuente: FuenteCorpus, creado_por_id: int, *, dry_run: bool
    ) -> ResultadoCargaFuente:
        """Procesa una fuente del manifiesto de punta a punta: descarga, valida, y (si no es
        `dry_run`) carga y procesa el documento.

        Nunca propaga una excepción: una fuente que falla en la descarga, la validación o el
        procesamiento se traduce a un resultado con estado `error`, para que no corte la carga
        de las demás fuentes del manifiesto.
        """
        limite_bytes = self._settings.max_upload_mb * _BYTES_POR_MB
        try:
            return await self._cargar_fuente_o_fallar(
                fuente, creado_por_id, limite_bytes, dry_run=dry_run
            )
        except DescargaInvalidaError as error:
            return ResultadoCargaFuente(fuente.id, "error", None, error.message)
        except ValidationError as error:
            mensajes = [mensaje for lista in (error.errors or {}).values() for mensaje in lista]
            return ResultadoCargaFuente(
                fuente.id, "error", None, "; ".join(mensajes) or error.message
            )
        except Exception:
            logger.exception("Falló la carga de la fuente '%s' del corpus normativo", fuente.id)
            return ResultadoCargaFuente(
                fuente.id, "error", None, "Error inesperado al cargar la fuente"
            )

    async def _cargar_fuente_o_fallar(
        self,
        fuente: FuenteCorpus,
        creado_por_id: int,
        limite_bytes: int,
        *,
        dry_run: bool,
    ) -> ResultadoCargaFuente:
        archivo = await self._descargador.descargar(fuente.url, limite_bytes)
        sha256 = hashlib.sha256(archivo.contenido).hexdigest()

        existente = await self._documento_service.buscar_por_sha256(sha256)
        if existente is not None:
            return ResultadoCargaFuente(
                fuente.id, "omitido", existente.id, f"ya cargado como documento #{existente.id}"
            )

        nombre_archivo = f"{fuente.id}.pdf"
        tipo_contenido = archivo.tipo_contenido or "application/pdf"
        idioma_normalizado = self._documento_service.validar_carga(
            nombre_archivo, tipo_contenido, len(archivo.contenido), fuente.idioma
        )

        if dry_run:
            tamano_kb = len(archivo.contenido) / 1024
            return ResultadoCargaFuente(
                fuente.id,
                "cargado",
                None,
                f"se cargaría ({tamano_kb:.0f} KB, idioma {idioma_normalizado})",
            )

        documento = await self._documento_service.cargar_de_fuente(
            nombre_archivo=nombre_archivo,
            tipo_contenido=tipo_contenido,
            contenido=archivo.contenido,
            idioma=idioma_normalizado,
            creado_por_id=creado_por_id,
            fuente_url=fuente.url,
        )
        await self._documento_service.procesar_ahora(documento.id)

        documento_final = await self._documento_service.obtener(documento.id)
        if documento_final.estado == "error":
            return ResultadoCargaFuente(
                fuente.id,
                "error",
                documento.id,
                documento_final.error_detalle or "No se pudo procesar el documento",
            )
        return ResultadoCargaFuente(
            fuente.id,
            "cargado",
            documento.id,
            f"{documento_final.paginas} páginas, {documento_final.cantidad_chunks} chunks",
        )
