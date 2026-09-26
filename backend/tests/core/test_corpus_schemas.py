"""Tests de validación del manifiesto de corpus (`ManifiestoCorpus`, `FuenteCorpus`)."""

from datetime import date

import pytest
from pydantic import ValidationError as PydanticValidationError

from ocr_rag.core.schemas.corpus import FuenteCorpus, ManifiestoCorpus


def _datos_fuente(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "cauca-recauca",
        "titulo": "Título de prueba",
        "url": "https://example.org/norma.pdf",
        "verificado": date(2026, 9, 26),
    }
    base.update(overrides)
    return base


def test_fuente_corpus_valida_acepta_los_campos_minimos() -> None:
    fuente = FuenteCorpus.model_validate(_datos_fuente())

    assert fuente.id == "cauca-recauca"
    assert fuente.idioma is None
    assert fuente.descripcion == ""
    assert fuente.licencia == ""


def test_fuente_corpus_con_id_en_formato_invalido_lanza_validation_error() -> None:
    with pytest.raises(PydanticValidationError, match="id"):
        FuenteCorpus.model_validate(_datos_fuente(id="CAUCA Recauca"))


def test_fuente_corpus_con_url_http_lanza_validation_error() -> None:
    with pytest.raises(PydanticValidationError, match="url"):
        FuenteCorpus.model_validate(_datos_fuente(url="http://example.org/norma.pdf"))


def test_fuente_corpus_con_idioma_en_formato_invalido_lanza_validation_error() -> None:
    with pytest.raises(PydanticValidationError, match="idioma"):
        FuenteCorpus.model_validate(_datos_fuente(idioma="ESPANOL"))


def test_fuente_corpus_con_idioma_compuesto_valido_lo_acepta() -> None:
    fuente = FuenteCorpus.model_validate(_datos_fuente(idioma="spa+eng"))

    assert fuente.idioma == "spa+eng"


def test_manifiesto_corpus_con_ids_duplicados_lanza_validation_error() -> None:
    datos = {
        "fuente": [
            _datos_fuente(id="norma-a"),
            _datos_fuente(id="norma-a", url="https://example.org/otra.pdf"),
        ]
    }

    with pytest.raises(PydanticValidationError, match="duplicados"):
        ManifiestoCorpus.model_validate(datos)


def test_manifiesto_corpus_con_ids_unicos_es_valido() -> None:
    datos = {
        "fuente": [
            _datos_fuente(id="norma-a"),
            _datos_fuente(id="norma-b", url="https://example.org/otra.pdf"),
        ]
    }

    manifiesto = ManifiestoCorpus.model_validate(datos)

    assert [fuente.id for fuente in manifiesto.fuente] == ["norma-a", "norma-b"]


def test_manifiesto_empaquetado_por_defecto_carga_y_valida() -> None:
    """El manifiesto `cli/corpus/normativa_centroamerica.toml` empaquetado con el CLI."""
    from ocr_rag.cli.cargar_corpus import cargar_manifiesto

    manifiesto = cargar_manifiesto(None)

    assert [fuente.id for fuente in manifiesto.fuente] == [
        "cauca-iv",
        "recauca-iv",
        "convenio-arancelario-aduanero",
    ]
    for fuente in manifiesto.fuente:
        assert fuente.url.startswith("https://")
        # La edición de la Imprenta Nacional de CR mezcla CAUCA III (derogado), CAUCA IV y el
        # reglamento viejo (Res. 101-2002): no debe volver al manifiesto.
        assert "imprentanacional.go.cr" not in fuente.url
