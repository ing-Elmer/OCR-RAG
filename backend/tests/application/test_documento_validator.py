"""Tests del `DocumentoValidator`."""

import pytest

from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.core.exceptions import NotFoundError, ValidationError
from ocr_rag.core.settings import get_settings
from tests.conftest import FakeDocumentoRepository


def _crear_validator() -> DocumentoValidator:
    return DocumentoValidator(FakeDocumentoRepository(), get_settings())


def test_validar_carga_archivo_valido_sin_idioma_usa_el_de_settings() -> None:
    validator = _crear_validator()

    idioma = validator.validar_carga("factura.pdf", "application/pdf", 1024, None)

    assert idioma == get_settings().tesseract_langs


def test_validar_carga_archivo_valido_con_idioma_devuelve_el_idioma_recibido() -> None:
    validator = _crear_validator()

    idioma = validator.validar_carga("foto.png", "image/png", 1024, "eng")

    assert idioma == "eng"


def test_validar_carga_extension_no_permitida_lanza_validation_error_en_archivo() -> None:
    validator = _crear_validator()

    with pytest.raises(ValidationError) as info:
        validator.validar_carga("documento.docx", "application/pdf", 1024, None)

    errores = info.value.errors
    assert errores is not None
    assert "archivo" in errores


def test_validar_carga_content_type_no_permitido_lanza_validation_error_en_archivo() -> None:
    validator = _crear_validator()

    with pytest.raises(ValidationError) as info:
        validator.validar_carga("documento.pdf", "application/octet-stream", 1024, None)

    errores = info.value.errors
    assert errores is not None
    assert "archivo" in errores


def test_validar_carga_archivo_vacio_lanza_validation_error_en_archivo() -> None:
    validator = _crear_validator()

    with pytest.raises(ValidationError) as info:
        validator.validar_carga("documento.pdf", "application/pdf", 0, None)

    errores = info.value.errors
    assert errores is not None
    assert "archivo" in errores


def test_validar_carga_archivo_supera_el_tamano_maximo_lanza_validation_error_en_archivo() -> None:
    validator = _crear_validator()
    demasiado_grande = (get_settings().max_upload_mb + 1) * 1024 * 1024

    with pytest.raises(ValidationError) as info:
        validator.validar_carga("documento.pdf", "application/pdf", demasiado_grande, None)

    errores = info.value.errors
    assert errores is not None
    assert "archivo" in errores


def test_validar_carga_idioma_con_formato_invalido_lanza_validation_error_en_idioma() -> None:
    validator = _crear_validator()

    with pytest.raises(ValidationError) as info:
        validator.validar_carga("documento.pdf", "application/pdf", 1024, "ESPANOL")

    errores = info.value.errors
    assert errores is not None
    assert "idioma" in errores


async def test_validar_existente_documento_inexistente_lanza_not_found() -> None:
    validator = _crear_validator()

    with pytest.raises(NotFoundError):
        await validator.validar_existente(99)


async def test_validar_existente_documento_existente_devuelve_sus_datos() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await repositorio.crear(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256="x" * 64,
    )
    validator = DocumentoValidator(repositorio, get_settings())

    documento = await validator.validar_existente(documento_id)

    assert documento.id == documento_id
    assert documento.nombre_archivo == "a.pdf"
