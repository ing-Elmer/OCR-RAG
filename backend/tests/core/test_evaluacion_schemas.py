"""Tests de validación del dataset de evaluación (`CasoEvaluacion`, `DatasetEvaluacion`)."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from ocr_rag.core.schemas.evaluacion import ArticuloEsperado, CasoEvaluacion, DatasetEvaluacion


def _datos_caso(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "transito-definicion",
        "pregunta": "¿Qué es el tránsito aduanero?",
        "esperados": [{"norma": "CAUCA IV", "articulo": "94"}],
    }
    base.update(overrides)
    return base


def test_caso_evaluacion_valido_acepta_los_campos_minimos() -> None:
    caso = CasoEvaluacion.model_validate(_datos_caso())

    assert caso.id == "transito-definicion"
    assert caso.esperados == [ArticuloEsperado(norma="CAUCA IV", articulo="94")]
    assert caso.nota == ""


def test_caso_evaluacion_admite_esperados_vacio_caso_negativo() -> None:
    caso = CasoEvaluacion.model_validate(_datos_caso(esperados=[]))

    assert caso.esperados == []


def test_caso_evaluacion_sin_pregunta_lanza_validation_error() -> None:
    datos = _datos_caso()
    del datos["pregunta"]

    with pytest.raises(PydanticValidationError, match="pregunta"):
        CasoEvaluacion.model_validate(datos)


def test_dataset_evaluacion_con_ids_duplicados_lanza_validation_error() -> None:
    datos = {"caso": [_datos_caso(id="a"), _datos_caso(id="a")]}

    with pytest.raises(PydanticValidationError, match="duplicados"):
        DatasetEvaluacion.model_validate(datos)


def test_dataset_evaluacion_con_ids_unicos_es_valido() -> None:
    datos = {"caso": [_datos_caso(id="a"), _datos_caso(id="b")]}

    dataset = DatasetEvaluacion.model_validate(datos)

    assert [caso.id for caso in dataset.caso] == ["a", "b"]


def test_dataset_empaquetado_por_defecto_carga_16_casos_y_normas_del_manifiesto() -> None:
    """El dataset `cli/evaluacion/normativa_ca.toml` empaquetado con el CLI."""
    from ocr_rag.cli.cargar_corpus import cargar_manifiesto
    from ocr_rag.cli.evaluar import cargar_dataset

    dataset = cargar_dataset(None)

    assert len(dataset.caso) == 16
    assert len({caso.id for caso in dataset.caso}) == 16

    normas_usadas = {esperado.norma for caso in dataset.caso for esperado in caso.esperados}
    normas_del_manifiesto = {
        fuente.norma for fuente in cargar_manifiesto(None).fuente if fuente.norma is not None
    }
    assert normas_usadas <= normas_del_manifiesto
