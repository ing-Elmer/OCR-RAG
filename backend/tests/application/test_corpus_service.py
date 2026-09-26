"""Tests del `CorpusService` (carga masiva del corpus normativo)."""

from datetime import date

from ocr_rag.application.services.corpus_service import CorpusService
from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.core.exceptions import DescargaInvalidaError
from ocr_rag.core.schemas.corpus import FuenteCorpus
from ocr_rag.core.settings import get_settings
from tests.conftest import (
    FakeBackgroundTaskQueue,
    FakeDescargadorHttp,
    FakeDocumentoRepository,
    FakeEmbeddingClient,
    FakeExtractorTexto,
)

_CREADO_POR_ID = 1


def _crear_corpus_service(
    repositorio: FakeDocumentoRepository, descargador: FakeDescargadorHttp
) -> CorpusService:
    validador = DocumentoValidator(repositorio, get_settings())
    procesador = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient()
    )
    documento_service = DocumentoService(
        repositorio, validador, procesador, FakeBackgroundTaskQueue()
    )
    return CorpusService(documento_service, descargador, get_settings())


def _fuente(**overrides: object) -> FuenteCorpus:
    base: dict[str, object] = {
        "id": "cauca-recauca",
        "titulo": "Código Aduanero Uniforme Centroamericano",
        "url": "https://example.org/cauca.pdf",
        "verificado": date(2026, 9, 26),
    }
    base.update(overrides)
    return FuenteCorpus.model_validate(base)


async def test_cargar_fuente_nueva_la_crea_y_procesa() -> None:
    repositorio = FakeDocumentoRepository()
    descargador = FakeDescargadorHttp()
    service = _crear_corpus_service(repositorio, descargador)

    resultado = await service.cargar_fuente(_fuente(), _CREADO_POR_ID, dry_run=False)

    assert resultado.estado == "cargado"
    assert resultado.documento_id is not None
    documento = await repositorio.obtener(resultado.documento_id)
    assert documento is not None
    assert documento.estado == "procesado"
    assert documento.fuente_url == "https://example.org/cauca.pdf"


async def test_cargar_fuente_ya_cargada_por_su_sha256_la_omite_sin_crear_otra() -> None:
    repositorio = FakeDocumentoRepository()
    descargador = FakeDescargadorHttp()
    service = _crear_corpus_service(repositorio, descargador)
    primero = await service.cargar_fuente(_fuente(), _CREADO_POR_ID, dry_run=False)

    segundo = await service.cargar_fuente(
        _fuente(id="otra-fuente", url="https://example.org/otra.pdf"),
        _CREADO_POR_ID,
        dry_run=False,
    )

    assert segundo.estado == "omitido"
    assert segundo.documento_id == primero.documento_id
    documentos, total = await repositorio.listar(limite=10, offset=0)
    assert total == 1


async def test_cargar_fuente_en_dry_run_no_escribe_ni_procesa() -> None:
    repositorio = FakeDocumentoRepository()
    descargador = FakeDescargadorHttp()
    service = _crear_corpus_service(repositorio, descargador)

    resultado = await service.cargar_fuente(_fuente(), _CREADO_POR_ID, dry_run=True)

    assert resultado.estado == "cargado"
    assert resultado.documento_id is None
    _documentos, total = await repositorio.listar(limite=10, offset=0)
    assert total == 0


async def test_cargar_fuente_con_descarga_invalida_devuelve_resultado_de_error() -> None:
    repositorio = FakeDocumentoRepository()
    descargador = FakeDescargadorHttp()
    fuente = _fuente()
    descargador.fallos[fuente.url] = DescargaInvalidaError("La url no usa https")
    service = _crear_corpus_service(repositorio, descargador)

    resultado = await service.cargar_fuente(fuente, _CREADO_POR_ID, dry_run=False)

    assert resultado.estado == "error"
    assert resultado.documento_id is None
    assert "https" in resultado.detalle
    _documentos, total = await repositorio.listar(limite=10, offset=0)
    assert total == 0


async def test_cargar_fuente_con_excepcion_inesperada_no_la_propaga() -> None:
    repositorio = FakeDocumentoRepository()
    descargador = FakeDescargadorHttp()
    fuente = _fuente()
    descargador.fallos[fuente.url] = RuntimeError("falla inesperada de red")
    service = _crear_corpus_service(repositorio, descargador)

    resultado = await service.cargar_fuente(fuente, _CREADO_POR_ID, dry_run=False)

    assert resultado.estado == "error"
    assert resultado.detalle
