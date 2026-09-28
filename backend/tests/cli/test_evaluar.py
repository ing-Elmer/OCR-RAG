"""Tests de las piezas puras de `cli evaluar`: sin red, sin base real, con fakes."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from ocr_rag.application.services.consulta_service import ConsultaService
from ocr_rag.application.validators.consulta_validator import ConsultaValidator
from ocr_rag.cli.evaluar import (
    calcular_resumen_de,
    cargar_dataset,
    evaluar_caso,
    evaluar_dataset,
    guardar_json,
)
from ocr_rag.core.schemas.documento import ChunkSimilar
from ocr_rag.core.schemas.evaluacion import ArticuloEsperado, CasoEvaluacion, DatasetEvaluacion
from ocr_rag.core.settings import get_settings
from tests.conftest import FakeChatClient, FakeDocumentoRepository, FakeEmbeddingClient


def _candidato(norma: str, articulo: str, documento_id: int = 1) -> ChunkSimilar:
    return ChunkSimilar(
        documento_id=documento_id,
        nombre_archivo="cauca-iv.pdf",
        orden=0,
        pagina=1,
        contenido=f"Artículo {articulo}. Texto de prueba de {norma}.",
        similitud=0.9,
        norma=norma,
        articulo=articulo,
        tipo_documento="normativa",
    )


def _crear_consulta_service(
    repositorio: FakeDocumentoRepository, chat_client: FakeChatClient
) -> ConsultaService:
    return ConsultaService(
        repositorio,
        ConsultaValidator(repositorio),
        FakeEmbeddingClient(),
        chat_client,
        get_settings(),
    )


# --- cargar_dataset (parser) -------------------------------------------------------------


def test_cargar_dataset_parsea_un_toml_valido(tmp_path: Path) -> None:
    ruta = tmp_path / "dataset.toml"
    ruta.write_text(
        '[[caso]]\nid = "a"\npregunta = "¿Qué es esto?"\n'
        'esperados = [{ norma = "CAUCA IV", articulo = "94" }]\n',
        encoding="utf-8",
    )

    dataset = cargar_dataset(ruta)

    assert [caso.id for caso in dataset.caso] == ["a"]


def test_cargar_dataset_con_ids_duplicados_lanza_validation_error(tmp_path: Path) -> None:
    ruta = tmp_path / "dataset.toml"
    ruta.write_text(
        '[[caso]]\nid = "a"\npregunta = "uno"\nesperados = []\n'
        '[[caso]]\nid = "a"\npregunta = "dos"\nesperados = []\n',
        encoding="utf-8",
    )

    with pytest.raises(PydanticValidationError, match="duplicados"):
        cargar_dataset(ruta)


def test_cargar_dataset_admite_esperados_vacio() -> None:
    dataset = DatasetEvaluacion.model_validate(
        {"caso": [{"id": "negativo", "pregunta": "¿Existe X?", "esperados": []}]}
    )

    assert dataset.caso[0].esperados == []


# --- evaluar_caso / evaluar_dataset (orquestación con ConsultaService real + fakes) -------


async def test_evaluar_caso_positivo_recupera_y_cita_correctamente() -> None:
    repositorio = FakeDocumentoRepository()
    repositorio.resultados_lexicos = [_candidato("CAUCA IV", "94")]
    chat_client = FakeChatClient(respuesta="El tránsito aduanero es... Art. 94 [1]")
    consulta_service = _crear_consulta_service(repositorio, chat_client)
    caso = CasoEvaluacion(
        id="transito-definicion",
        pregunta="¿Qué es el tránsito aduanero?",
        esperados=[ArticuloEsperado(norma="CAUCA IV", articulo="94")],
    )

    resultado = await evaluar_caso(caso, consulta_service, top_k=8)

    assert resultado.recuperacion.acierto is True
    assert resultado.recuperacion.posicion == 1
    assert (resultado.citas_logradas, resultado.citas_totales) == (1, 1)
    assert resultado.fuentes[0]["norma"] == "CAUCA IV"


async def test_evaluar_caso_negativo_sin_fuentes_es_acierto() -> None:
    repositorio = FakeDocumentoRepository()
    chat_client = FakeChatClient(
        respuesta="No encontré información relevante en los documentos cargados."
    )
    consulta_service = _crear_consulta_service(repositorio, chat_client)
    caso = CasoEvaluacion(id="negativo", pregunta="¿Existe una norma sobre X?", esperados=[])

    resultado = await evaluar_caso(caso, consulta_service, top_k=8)

    assert resultado.recuperacion.acierto is True
    assert (resultado.citas_logradas, resultado.citas_totales) == (0, 0)


async def test_evaluar_dataset_corre_todos_los_casos_en_orden() -> None:
    repositorio = FakeDocumentoRepository()
    repositorio.resultados_lexicos = [_candidato("CAUCA IV", "94")]
    chat_client = FakeChatClient(respuesta="Respuesta con Art. 94 [1]")
    consulta_service = _crear_consulta_service(repositorio, chat_client)
    dataset = DatasetEvaluacion(
        caso=[
            CasoEvaluacion(id="uno", pregunta="¿Pregunta uno?", esperados=[]),
            CasoEvaluacion(id="dos", pregunta="¿Pregunta dos?", esperados=[]),
        ]
    )

    resultados = await evaluar_dataset(dataset, consulta_service, top_k=8)

    assert [resultado.id for resultado in resultados] == ["uno", "dos"]


# --- guardar_json --------------------------------------------------------------------------


async def test_guardar_json_vuelca_el_detalle_completo(tmp_path: Path) -> None:
    repositorio = FakeDocumentoRepository()
    repositorio.resultados_lexicos = [_candidato("CAUCA IV", "94")]
    chat_client = FakeChatClient(respuesta="Respuesta con Art. 94 [1]")
    consulta_service = _crear_consulta_service(repositorio, chat_client)
    caso = CasoEvaluacion(
        id="transito-definicion",
        pregunta="¿Qué es el tránsito aduanero?",
        esperados=[ArticuloEsperado(norma="CAUCA IV", articulo="94")],
    )
    resultado = await evaluar_caso(caso, consulta_service, top_k=8)
    ruta = tmp_path / "salida.json"

    guardar_json(ruta, [resultado], calcular_resumen_de([resultado]))

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["resumen"]["hit_at_k"] == 1.0
    assert datos["casos"][0]["id"] == "transito-definicion"
    assert datos["casos"][0]["citasLogradas"] == 1
