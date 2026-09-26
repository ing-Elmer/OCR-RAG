"""Worker del pipeline OCR + RAG: extrae texto, arma chunks y genera sus embeddings.

Se invoca siempre desde `BackgroundTaskQueue`, nunca dentro del ciclo de un request HTTP.
"""

import logging

from ocr_rag.application.chunking import dividir_en_chunks
from ocr_rag.core.clients import EmbeddingClient, ExtractorTexto
from ocr_rag.core.repositories import DocumentoRepository
from ocr_rag.core.schemas.documento import ChunkParaGuardar

logger = logging.getLogger(__name__)

# Cantidad máxima de textos por llamada de embeddings, para no exceder los límites de la API.
_TAMANO_LOTE_EMBEDDINGS = 100

_MENSAJE_ERROR_GENERICO = "No se pudo procesar el documento"
_MENSAJE_SIN_TEXTO = "No se pudo extraer texto del documento"


class ProcesamientoDocumentoService:
    """Procesa un documento: OCR/extracción de texto, chunking, embeddings y persistencia."""

    def __init__(
        self,
        repositorio: DocumentoRepository,
        extractor: ExtractorTexto,
        embedding_client: EmbeddingClient,
    ) -> None:
        self._repositorio = repositorio
        self._extractor = extractor
        self._embedding_client = embedding_client

    async def procesar(self, documento_id: int) -> None:
        """Ejecuta el pipeline completo para `documento_id`.

        Nunca propaga una excepción: cualquier falla deja el documento en estado `error` con un
        mensaje genérico en español; el detalle técnico solo se loguea (nunca el texto del
        documento ni credenciales).
        """
        documento = await self._repositorio.obtener_para_procesar(documento_id)
        if documento is None:
            logger.warning(
                "Se descarta el procesamiento: el documento %s ya no existe", documento_id
            )
            return

        await self._repositorio.marcar_procesando(documento_id)
        try:
            paginas = await self._extractor.extraer(
                documento.contenido, documento.tipo_contenido, documento.idioma
            )
            if not any(pagina.texto.strip() for pagina in paginas):
                await self._repositorio.marcar_error(documento_id, _MENSAJE_SIN_TEXTO)
                return

            chunks_de_texto = dividir_en_chunks(paginas)
            if not chunks_de_texto:
                await self._repositorio.marcar_error(documento_id, _MENSAJE_SIN_TEXTO)
                return

            embeddings = await self._generar_embeddings_en_lotes(
                [chunk.contenido for chunk in chunks_de_texto]
            )
            chunks_para_guardar = [
                ChunkParaGuardar(
                    orden=chunk.orden,
                    contenido=chunk.contenido,
                    pagina=chunk.pagina,
                    embedding=embedding,
                )
                for chunk, embedding in zip(chunks_de_texto, embeddings, strict=True)
            ]
            await self._repositorio.guardar_resultado(
                documento_id, len(paginas), chunks_para_guardar
            )
        except Exception:
            logger.exception("Falló el procesamiento OCR del documento %s", documento_id)
            await self._repositorio.marcar_error(documento_id, _MENSAJE_ERROR_GENERICO)

    async def _generar_embeddings_en_lotes(self, textos: list[str]) -> list[list[float]]:
        """Genera los embeddings en lotes de a lo sumo `_TAMANO_LOTE_EMBEDDINGS` textos."""
        embeddings: list[list[float]] = []
        for inicio in range(0, len(textos), _TAMANO_LOTE_EMBEDDINGS):
            lote = textos[inicio : inicio + _TAMANO_LOTE_EMBEDDINGS]
            embeddings.extend(await self._embedding_client.generar_embeddings(lote))
        return embeddings
