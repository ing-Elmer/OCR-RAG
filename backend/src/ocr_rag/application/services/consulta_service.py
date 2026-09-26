"""Service de consultas (RAG): busca los chunks más relevantes y arma la respuesta con el chat."""

import logging

from ocr_rag.application.validators.consulta_validator import ConsultaValidator
from ocr_rag.core.clients import ChatClient, EmbeddingClient
from ocr_rag.core.repositories import DocumentoRepository
from ocr_rag.core.schemas.documento import ConsultaResponse, FuenteConsulta
from ocr_rag.core.settings import Settings

logger = logging.getLogger(__name__)

_MENSAJE_SIN_RESULTADOS = "No encontré información relevante en los documentos cargados."

# Largo del fragmento de texto que se muestra como fuente de una respuesta.
_LARGO_FRAGMENTO = 300


class ConsultaService:
    """Resuelve una pregunta en lenguaje natural contra el corpus de documentos procesados."""

    def __init__(
        self,
        repositorio: DocumentoRepository,
        validador: ConsultaValidator,
        embedding_client: EmbeddingClient,
        chat_client: ChatClient,
        settings: Settings,
    ) -> None:
        self._repositorio = repositorio
        self._validador = validador
        self._embedding_client = embedding_client
        self._chat_client = chat_client
        self._settings = settings

    async def consultar(
        self, pregunta: str, documento_ids: list[int] | None, top_k: int
    ) -> ConsultaResponse:
        """Busca los `top_k` chunks más similares a `pregunta` y le pide al chat que responda.

        Si ningún chunk supera `Settings.rag_similitud_minima`, responde un mensaje fijo sin
        llamar al modelo de chat.
        """
        await self._validador.validar_documentos(documento_ids)

        embeddings_pregunta = await self._embedding_client.generar_embeddings([pregunta])
        embedding_pregunta = embeddings_pregunta[0]

        similares = await self._repositorio.buscar_similares(
            embedding_pregunta, top_k, documento_ids
        )
        relevantes = [
            chunk for chunk in similares if chunk.similitud >= self._settings.rag_similitud_minima
        ]
        if not relevantes:
            return ConsultaResponse(respuesta=_MENSAJE_SIN_RESULTADOS, fuentes=[])

        contextos = [
            f"[{indice}] {chunk.contenido}" for indice, chunk in enumerate(relevantes, start=1)
        ]
        respuesta = await self._chat_client.responder(pregunta, contextos)

        fuentes = [
            FuenteConsulta(
                documento_id=chunk.documento_id,
                nombre_archivo=chunk.nombre_archivo,
                orden=chunk.orden,
                pagina=chunk.pagina,
                fragmento=chunk.contenido[:_LARGO_FRAGMENTO],
                similitud=chunk.similitud,
                fuente_url=chunk.fuente_url,
            )
            for chunk in relevantes
        ]
        return ConsultaResponse(respuesta=respuesta, fuentes=fuentes)
