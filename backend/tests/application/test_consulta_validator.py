"""Tests del `ConsultaValidator`."""

import pytest

from ocr_rag.application.validators.consulta_validator import ConsultaValidator
from ocr_rag.core.exceptions import ValidationError
from tests.conftest import FakeDocumentoRepository


async def _crear_documento_procesado(repositorio: FakeDocumentoRepository) -> int:
    documento_id = await repositorio.crear(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256="a" * 64,
    )
    tomado = await repositorio.tomar_para_procesar(documento_id)
    assert tomado is not None
    await repositorio.guardar_resultado(
        documento_id, paginas=1, chunks=[], version_procesamiento=tomado.version_procesamiento
    )
    return documento_id


async def test_validar_documentos_sin_filtro_no_hace_nada() -> None:
    validator = ConsultaValidator(FakeDocumentoRepository())

    await validator.validar_documentos(None)
    await validator.validar_documentos([])


async def test_validar_documentos_todos_procesados_no_lanza() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_procesado(repositorio)
    validator = ConsultaValidator(repositorio)

    await validator.validar_documentos([documento_id])


async def test_validar_documentos_con_id_inexistente_lanza_validation_error() -> None:
    validator = ConsultaValidator(FakeDocumentoRepository())

    with pytest.raises(ValidationError) as info:
        await validator.validar_documentos([999])

    errores = info.value.errors
    assert errores is not None
    assert "documentoIds" in errores


async def test_validar_documentos_con_documento_no_procesado_lanza_validation_error() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await repositorio.crear(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256="a" * 64,
    )
    validator = ConsultaValidator(repositorio)

    with pytest.raises(ValidationError):
        await validator.validar_documentos([documento_id])
