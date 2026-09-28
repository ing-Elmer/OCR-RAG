"""Tests de `DocumentoActualizacionRequest` (`PATCH /api/documentos/{id}`).

Distingue un campo ausente (no tocar) de uno presente con valor `null` (limpiarlo) vía
`model_fields_set`; estos tests cubren esa semántica.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from ocr_rag.core.schemas.documento import DocumentoActualizacionRequest


def test_solo_tipo_documento_no_toca_norma() -> None:
    request = DocumentoActualizacionRequest.model_validate({"tipoDocumento": "contrato"})

    assert request.model_fields_set == {"tipo_documento"}
    assert request.tipo_documento == "contrato"


def test_norma_null_explicito_queda_marcado_para_limpiarla() -> None:
    request = DocumentoActualizacionRequest.model_validate({"norma": None})

    assert request.model_fields_set == {"norma"}
    assert request.norma is None


def test_norma_con_texto_la_actualiza() -> None:
    request = DocumentoActualizacionRequest.model_validate({"norma": "CAUCA IV"})

    assert request.model_fields_set == {"norma"}
    assert request.norma == "CAUCA IV"


def test_ambos_campos_presentes() -> None:
    request = DocumentoActualizacionRequest.model_validate(
        {"tipoDocumento": "normativa", "norma": "RECAUCA IV"}
    )

    assert request.model_fields_set == {"tipo_documento", "norma"}


def test_body_vacio_lanza_validation_error() -> None:
    with pytest.raises(PydanticValidationError, match="al menos un campo"):
        DocumentoActualizacionRequest.model_validate({})


def test_tipo_documento_null_explicito_lanza_validation_error() -> None:
    with pytest.raises(PydanticValidationError, match="no puede ser nulo"):
        DocumentoActualizacionRequest.model_validate({"tipoDocumento": None})


def test_tipo_documento_invalido_lanza_validation_error() -> None:
    with pytest.raises(PydanticValidationError):
        DocumentoActualizacionRequest.model_validate({"tipoDocumento": "factura"})


def test_norma_vacia_lanza_validation_error() -> None:
    with pytest.raises(PydanticValidationError):
        DocumentoActualizacionRequest.model_validate({"norma": ""})


def test_norma_demasiado_larga_lanza_validation_error() -> None:
    with pytest.raises(PydanticValidationError):
        DocumentoActualizacionRequest.model_validate({"norma": "x" * 101})
