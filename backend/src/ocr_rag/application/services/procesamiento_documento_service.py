"""Worker del pipeline OCR + RAG: extrae texto, arma chunks y genera sus embeddings.

Se invoca siempre desde `BackgroundTaskQueue`, nunca dentro del ciclo de un request HTTP.
"""

import logging

from ocr_rag.application.chunking import dividir_en_chunks
from ocr_rag.application.limpieza_paginas import limpiar_encabezados_pies
from ocr_rag.core.clients import ClasificadorDocumento, EmbeddingClient, ExtractorTexto
from ocr_rag.core.repositories import DocumentoRepository
from ocr_rag.core.schemas.documento import ChunkParaGuardar, PaginaExtraida, TipoDocumento

logger = logging.getLogger(__name__)

# Cantidad máxima de textos por llamada de embeddings, para no exceder los límites de la API.
_TAMANO_LOTE_EMBEDDINGS = 100

# Largo de la muestra de texto que se le pasa al clasificador automático de documentos.
_LARGO_MUESTRA_CLASIFICACION = 3000

_MENSAJE_ERROR_GENERICO = "No se pudo procesar el documento"
_MENSAJE_SIN_TEXTO = "No se pudo extraer texto del documento"


class ProcesamientoDocumentoService:
    """Procesa un documento: OCR/extracción de texto, chunking, embeddings y persistencia."""

    def __init__(
        self,
        repositorio: DocumentoRepository,
        extractor: ExtractorTexto,
        embedding_client: EmbeddingClient,
        clasificador: ClasificadorDocumento,
    ) -> None:
        self._repositorio = repositorio
        self._extractor = extractor
        self._embedding_client = embedding_client
        self._clasificador = clasificador

    async def procesar(self, documento_id: int) -> bool:
        """Toma `documento_id` en forma exclusiva y ejecuta el pipeline completo sobre él.

        Si `clasificacion_pendiente` (leído de la base al tomar el documento, nunca de un
        parámetro en memoria) sigue en `True`, clasifica el documento con `ClasificadorDocumento`
        después de extraer el texto, y guarda el tipo resultante antes de armar los chunks; si
        una edición manual cambió el tipo mientras tanto, esa edición gana y se usa para
        chunkear. Antes de chunkear, limpia de las páginas los encabezados y pies repetidos
        (`limpiar_encabezados_pies`); si el tipo de documento (indicado o clasificado) es
        `"normativa"`, el chunking corta además por artículo.

        Devuelve `False` sin hacer nada si no pudo tomar el documento (no existe, o ya lo tiene
        tomado otro proceso); `True` si lo tomó, haya terminado el procesamiento en éxito,
        error, o descartado por una versión más nueva. Nunca propaga una excepción: cualquier
        falla deja el documento en estado `error` con un mensaje genérico en español; el detalle
        técnico solo se loguea (nunca el texto del documento ni credenciales).
        """
        documento = await self._repositorio.tomar_para_procesar(documento_id)
        if documento is None:
            logger.info(
                "Se omite el procesamiento del documento %s: no existe o ya lo tiene tomado "
                "otro proceso",
                documento_id,
            )
            return False

        version = documento.version_procesamiento
        try:
            paginas = await self._extractor.extraer(
                documento.contenido, documento.tipo_contenido, documento.idioma
            )
            if not any(pagina.texto.strip() for pagina in paginas):
                await self._marcar_error_si_version_vigente(
                    documento_id, _MENSAJE_SIN_TEXTO, version
                )
                return True

            tipo_documento_efectivo = await self._resolver_tipo_documento(
                documento_id,
                documento.tipo_documento,
                documento.clasificacion_pendiente,
                paginas,
                version,
            )

            paginas_limpias = limpiar_encabezados_pies(paginas)
            chunks_de_texto = dividir_en_chunks(
                paginas_limpias, tipo_documento=tipo_documento_efectivo
            )
            if not chunks_de_texto:
                await self._marcar_error_si_version_vigente(
                    documento_id, _MENSAJE_SIN_TEXTO, version
                )
                return True

            embeddings = await self._generar_embeddings_en_lotes(
                [chunk.contenido for chunk in chunks_de_texto]
            )
            chunks_para_guardar = [
                ChunkParaGuardar(
                    orden=chunk.orden,
                    contenido=chunk.contenido,
                    pagina=chunk.pagina,
                    embedding=embedding,
                    articulo=chunk.articulo,
                )
                for chunk, embedding in zip(chunks_de_texto, embeddings, strict=True)
            ]
            guardado = await self._repositorio.guardar_resultado(
                documento_id, len(paginas), chunks_para_guardar, version
            )
            if not guardado:
                logger.info(
                    "Se descarta el resultado del documento %s: ya hay un procesamiento más "
                    "nuevo en curso",
                    documento_id,
                )
        except Exception:
            logger.exception("Falló el procesamiento OCR del documento %s", documento_id)
            await self._marcar_error_si_version_vigente(
                documento_id, _MENSAJE_ERROR_GENERICO, version
            )
        return True

    async def _marcar_error_si_version_vigente(
        self, documento_id: int, mensaje: str, version_procesamiento: int
    ) -> None:
        """Marca error solo si `version_procesamiento` sigue vigente; si no, no toca el
        documento (ya hay un procesamiento más nuevo en curso) y solo lo loguea.
        """
        aplicado = await self._repositorio.marcar_error(
            documento_id, mensaje, version_procesamiento
        )
        if not aplicado:
            logger.info(
                "Se descarta el error del documento %s: ya hay un procesamiento más nuevo en curso",
                documento_id,
            )

    async def _resolver_tipo_documento(
        self,
        documento_id: int,
        tipo_documento_tomado: TipoDocumento,
        clasificacion_pendiente: bool,
        paginas: list[PaginaExtraida],
        version_procesamiento: int,
    ) -> TipoDocumento:
        """Si la clasificación seguía pendiente al tomar el documento, lo clasifica y guarda el
        resultado; si una edición manual del tipo llegó primero (o hay una versión más nueva en
        curso), respeta esa edición y relee el tipo vigente. Si no estaba pendiente, devuelve el
        tipo tal cual se tomó.
        """
        if not clasificacion_pendiente:
            return tipo_documento_tomado

        muestra = _armar_muestra_para_clasificar(paginas)
        tipo_clasificado = await self._clasificador.clasificar(muestra)
        aplicado = await self._repositorio.actualizar_clasificacion(
            documento_id, tipo_clasificado, version_procesamiento
        )
        if aplicado:
            return tipo_clasificado

        documento_actual = await self._repositorio.obtener(documento_id)
        if documento_actual is not None:
            return documento_actual.tipo_documento
        return tipo_documento_tomado

    async def _generar_embeddings_en_lotes(self, textos: list[str]) -> list[list[float]]:
        """Genera los embeddings en lotes de a lo sumo `_TAMANO_LOTE_EMBEDDINGS` textos."""
        embeddings: list[list[float]] = []
        for inicio in range(0, len(textos), _TAMANO_LOTE_EMBEDDINGS):
            lote = textos[inicio : inicio + _TAMANO_LOTE_EMBEDDINGS]
            embeddings.extend(await self._embedding_client.generar_embeddings(lote))
        return embeddings


def _armar_muestra_para_clasificar(paginas: list[PaginaExtraida]) -> str:
    """Concatena el texto de `paginas` (en orden) y lo recorta a `_LARGO_MUESTRA_CLASIFICACION`
    caracteres, para pasárselo al clasificador automático de documentos.
    """
    texto = "\n\n".join(pagina.texto for pagina in paginas if pagina.texto.strip())
    return texto[:_LARGO_MUESTRA_CLASIFICACION]
