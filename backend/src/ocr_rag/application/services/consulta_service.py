"""Service de consultas (RAG): busca los chunks más relevantes y arma la respuesta con el chat."""

import logging

from ocr_rag.application.busqueda_hibrida import fusionar_rrf
from ocr_rag.application.validators.consulta_validator import ConsultaValidator
from ocr_rag.core.clients import ChatClient, EmbeddingClient
from ocr_rag.core.repositories import DocumentoRepository
from ocr_rag.core.schemas.documento import (
    ConsultaResponse,
    FragmentoContexto,
    FuenteConsulta,
    TipoDocumento,
)
from ocr_rag.core.settings import Settings

logger = logging.getLogger(__name__)

_MENSAJE_SIN_RESULTADOS = "No encontré información relevante en los documentos cargados."

# Largo del fragmento de texto que se muestra como fuente de una respuesta.
_LARGO_FRAGMENTO = 300

# Cantidad de candidatos que se piden a cada búsqueda (vectorial y léxica) antes de fusionarlos
# con RRF; es independiente del `top_k` final que pide la consulta.
_TOP_K_CANDIDATOS = 20


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
        self,
        pregunta: str,
        documento_ids: list[int] | None,
        top_k: int,
        tipos_documento: list[TipoDocumento] | None = None,
    ) -> ConsultaResponse:
        """Busca los `top_k` chunks más relevantes para `pregunta` y le pide al chat que
        responda, combinando búsqueda vectorial y léxica (Reciprocal Rank Fusion).

        Si se indica `tipos_documento`, restringe la búsqueda a esas categorías. Antes de
        fusionar, descarta los candidatos vectoriales que no superan
        `Settings.rag_similitud_minima` (los léxicos se mantienen siempre: una coincidencia de
        texto completo es una señal real, aunque su similitud vectorial sea baja); así, con un
        `top_k` chico, un candidato vectorial débil no puede desplazar a una coincidencia léxica
        genuina. Responde un mensaje fijo sin llamar al modelo de chat si, después de ese
        filtro y de fusionar, no queda ningún candidato.
        """
        await self._validador.validar_documentos(documento_ids)

        embeddings_pregunta = await self._embedding_client.generar_embeddings([pregunta])
        embedding_pregunta = embeddings_pregunta[0]

        candidatos_vectoriales = await self._repositorio.buscar_candidatos_vectoriales(
            embedding_pregunta, _TOP_K_CANDIDATOS, documento_ids, tipos_documento
        )
        candidatos_lexicos = await self._repositorio.buscar_candidatos_lexicos(
            pregunta, embedding_pregunta, _TOP_K_CANDIDATOS, documento_ids, tipos_documento
        )

        candidatos_vectoriales_relevantes = [
            candidato
            for candidato in candidatos_vectoriales
            if candidato.similitud >= self._settings.rag_similitud_minima
        ]
        relevantes = fusionar_rrf(candidatos_vectoriales_relevantes, candidatos_lexicos, top_k)
        if not relevantes:
            return ConsultaResponse(respuesta=_MENSAJE_SIN_RESULTADOS, fuentes=[])

        fragmentos = [
            FragmentoContexto(
                numero=indice,
                contenido=chunk.contenido,
                nombre_archivo=chunk.nombre_archivo,
                norma=chunk.norma,
                articulo=chunk.articulo,
                pagina=chunk.pagina,
            )
            for indice, chunk in enumerate(relevantes, start=1)
        ]
        respuesta = await self._chat_client.responder(pregunta, fragmentos)

        fuentes = [
            FuenteConsulta(
                documento_id=chunk.documento_id,
                nombre_archivo=chunk.nombre_archivo,
                orden=chunk.orden,
                pagina=chunk.pagina,
                fragmento=chunk.contenido[:_LARGO_FRAGMENTO],
                similitud=chunk.similitud,
                fuente_url=chunk.fuente_url,
                norma=chunk.norma,
                articulo=chunk.articulo,
                tipo_documento=chunk.tipo_documento,
            )
            for chunk in relevantes
        ]
        return ConsultaResponse(respuesta=respuesta, fuentes=fuentes)
