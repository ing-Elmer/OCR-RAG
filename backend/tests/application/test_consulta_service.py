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


async def test_consultar_sin_candidatos_relevantes_no_llama_al_chat() -> None:
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    repositorio.resultados_vectoriales = [
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


async def test_consultar_con_resultados_vectoriales_relevantes_arma_fragmentos_y_fuentes() -> None:
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    repositorio.resultados_vectoriales = [
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
    _, fragmentos = chat_client.llamadas[0]
    assert [f.numero for f in fragmentos] == [1, 2]
    assert fragmentos[0].contenido == "Contenido relevante número uno."
    assert fragmentos[0].nombre_archivo == "a.pdf"


async def test_consultar_solo_con_candidatos_lexicos_igual_llama_al_chat() -> None:
    """Un chunk que solo entra por texto completo (sin superar el umbral vectorial) no debe
    descartarse: la búsqueda léxica encontró una coincidencia real.
    """
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    repositorio.resultados_vectoriales = []
    repositorio.resultados_lexicos = [
        ChunkSimilar(
            documento_id=1,
            nombre_archivo="a.pdf",
            orden=0,
            pagina=1,
            contenido="Tránsito aduanero: definición y requisitos.",
            similitud=umbral - 0.05,
            norma="CAUCA IV",
            articulo="94",
        )
    ]
    chat_client = FakeChatClient(respuesta="El tránsito aduanero es... [1]")
    service = _crear_service(repositorio, chat_client)

    resultado = await service.consultar("¿Qué es el tránsito aduanero?", None, top_k=5)

    assert resultado.respuesta == "El tránsito aduanero es... [1]"
    assert len(resultado.fuentes) == 1
    assert resultado.fuentes[0].norma == "CAUCA IV"
    assert resultado.fuentes[0].articulo == "94"
    assert len(chat_client.llamadas) == 1


async def test_consultar_fusiona_candidatos_vectoriales_y_lexicos_con_rrf() -> None:
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    chunk_en_ambas = ChunkSimilar(
        documento_id=1,
        nombre_archivo="a.pdf",
        orden=0,
        pagina=1,
        contenido="Aparece en ambas búsquedas.",
        similitud=umbral + 0.5,
    )
    chunk_solo_vectorial = ChunkSimilar(
        documento_id=2,
        nombre_archivo="b.pdf",
        orden=0,
        pagina=1,
        contenido="Solo semántico.",
        similitud=umbral + 0.4,
    )
    repositorio.resultados_vectoriales = [chunk_solo_vectorial, chunk_en_ambas]
    repositorio.resultados_lexicos = [chunk_en_ambas]
    service = _crear_service(repositorio, FakeChatClient())

    resultado = await service.consultar("pregunta", None, top_k=5)

    # El chunk presente en ambas listas suma los dos aportes de RRF y queda primero, aunque en
    # la lista vectorial estuviera en segundo lugar.
    ids_en_orden = [(f.documento_id, f.orden) for f in resultado.fuentes]
    assert ids_en_orden[0] == (1, 0)


async def test_consultar_con_topk_bajo_no_pierde_la_coincidencia_lexica_por_ruido_vectorial() -> (
    None
):
    """Con `top_k` chico, 20 candidatos vectoriales débiles (por debajo del umbral) no deben
    desplazar a la única coincidencia léxica real, que se mantiene siempre.
    """
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    repositorio.resultados_vectoriales = [
        ChunkSimilar(
            documento_id=100 + indice,
            nombre_archivo=f"ruido-{indice}.pdf",
            orden=0,
            pagina=1,
            contenido=f"Ruido semántico {indice}.",
            similitud=umbral - 0.01,
        )
        for indice in range(20)
    ]
    repositorio.resultados_lexicos = [
        ChunkSimilar(
            documento_id=1,
            nombre_archivo="cauca.pdf",
            orden=0,
            pagina=1,
            contenido="Tránsito aduanero: definición y requisitos.",
            similitud=umbral - 0.2,
            norma="CAUCA IV",
            articulo="94",
        )
    ]
    chat_client = FakeChatClient(respuesta="El tránsito aduanero es... [1]")
    service = _crear_service(repositorio, chat_client)

    resultado = await service.consultar("¿Qué es el tránsito aduanero?", None, top_k=1)

    assert len(resultado.fuentes) == 1
    assert resultado.fuentes[0].articulo == "94"
    assert len(chat_client.llamadas) == 1


async def test_consultar_todo_bajo_el_umbral_y_sin_lexicos_no_llama_al_chat() -> None:
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    repositorio.resultados_vectoriales = [
        ChunkSimilar(
            documento_id=100 + indice,
            nombre_archivo=f"ruido-{indice}.pdf",
            orden=0,
            pagina=1,
            contenido=f"Ruido semántico {indice}.",
            similitud=umbral - 0.01,
        )
        for indice in range(20)
    ]
    chat_client = FakeChatClient()
    service = _crear_service(repositorio, chat_client)

    resultado = await service.consultar("pregunta", None, top_k=1)

    assert resultado.fuentes == []
    assert chat_client.llamadas == []


async def test_consultar_con_documento_ids_invalidos_lanza_validation_error() -> None:
    repositorio = FakeDocumentoRepository()
    service = _crear_service(repositorio, FakeChatClient())

    with pytest.raises(ValidationError):
        await service.consultar("pregunta", [999], top_k=5)


async def test_consultar_con_tipos_documento_filtra_los_resultados_del_repositorio() -> None:
    repositorio = FakeDocumentoRepository()
    umbral = get_settings().rag_similitud_minima
    repositorio.resultados_vectoriales = [
        ChunkSimilar(
            documento_id=1,
            nombre_archivo="a.pdf",
            orden=0,
            pagina=1,
            contenido="Contenido normativo relevante.",
            similitud=umbral + 0.5,
            tipo_documento="normativa",
        ),
        ChunkSimilar(
            documento_id=2,
            nombre_archivo="b.pdf",
            orden=0,
            pagina=1,
            contenido="Contenido de un contrato.",
            similitud=umbral + 0.5,
            tipo_documento="contrato",
        ),
    ]
    service = _crear_service(repositorio, FakeChatClient())

    resultado = await service.consultar(
        "¿Qué dice la norma?", None, top_k=5, tipos_documento=["normativa"]
    )

    assert len(resultado.fuentes) == 1
    assert resultado.fuentes[0].documento_id == 1
    assert resultado.fuentes[0].tipo_documento == "normativa"
