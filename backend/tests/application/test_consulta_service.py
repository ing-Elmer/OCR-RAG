"""Tests del `ConsultaService`."""

import pytest

from ocr_rag.application.services.consulta_service import ConsultaService
from ocr_rag.application.validators.consulta_validator import ConsultaValidator
from ocr_rag.core.exceptions import ValidationError
from ocr_rag.core.schemas.documento import ChunkSimilar
from ocr_rag.core.settings import get_settings
from tests.conftest import FakeChatClient, FakeDocumentoRepository, FakeEmbeddingClient


def _crear_service(
    repositorio: FakeDocumentoRepository, chat_client: FakeChatClient
) -> ConsultaService:
    return ConsultaService(
        repositorio,
        ConsultaValidator(repositorio),
        FakeEmbeddingClient(),
        chat_client,
        get_settings(),
    )


async def test_consultar_sin_resultados_sobre_el_umbral_no_llama_al_chat() -> None:
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    repositorio.resultados_similares = [
        ChunkSimilar(
            documento_id=1,
            nombre_archivo="a.pdf",
            orden=0,
            pagina=1,
            contenido="contenido poco relevante",
            similitud=umbral - 0.1,
        )
    ]
    chat_client = FakeChatClient()
    service = _crear_service(repositorio, chat_client)

    resultado = await service.consultar("¿Qué dice el documento?", None, top_k=5)

    assert resultado.fuentes == []
    assert resultado.respuesta == "No encontré información relevante en los documentos cargados."
    assert chat_client.llamadas == []


async def test_consultar_con_resultados_relevantes_arma_contextos_numerados_y_fuentes() -> None:
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    repositorio.resultados_similares = [
        ChunkSimilar(
            documento_id=1,
            nombre_archivo="a.pdf",
            orden=0,
            pagina=1,
            contenido="Contenido relevante número uno.",
            similitud=umbral + 0.5,
        ),
        ChunkSimilar(
            documento_id=2,
            nombre_archivo="b.pdf",
            orden=3,
            pagina=None,
            contenido="Contenido relevante número dos.",
            similitud=umbral + 0.3,
        ),
    ]
    chat_client = FakeChatClient(respuesta="La respuesta es X [1][2].")
    service = _crear_service(repositorio, chat_client)

    resultado = await service.consultar("¿Qué dice el documento?", None, top_k=5)

    assert resultado.respuesta == "La respuesta es X [1][2]."
    assert len(resultado.fuentes) == 2
    assert resultado.fuentes[0].documento_id == 1
    assert resultado.fuentes[0].fragmento == "Contenido relevante número uno."
    assert resultado.fuentes[1].pagina is None

    assert len(chat_client.llamadas) == 1
    _, contextos = chat_client.llamadas[0]
    assert contextos[0].startswith("[1] ")
    assert contextos[1].startswith("[2] ")


async def test_consultar_con_documento_ids_invalidos_lanza_validation_error() -> None:
    repositorio = FakeDocumentoRepository()
    service = _crear_service(repositorio, FakeChatClient())

    with pytest.raises(ValidationError):
        await service.consultar("pregunta", [999], top_k=5)
