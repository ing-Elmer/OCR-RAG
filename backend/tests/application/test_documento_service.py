"""Tests del `DocumentoService`."""

import hashlib

from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.core.settings import get_settings
from tests.conftest import (
    FakeBackgroundTaskQueue,
    FakeDocumentoRepository,
    FakeEmbeddingClient,
    FakeExtractorTexto,
)


def _crear_service(
    repositorio: FakeDocumentoRepository, cola: FakeBackgroundTaskQueue
) -> DocumentoService:
    procesador = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient()
    )
    return DocumentoService(
        repositorio, DocumentoValidator(repositorio, get_settings()), procesador, cola
    )


async def test_cargar_documento_valido_lo_guarda_pendiente_y_encola_su_procesamiento() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)

    documento = await service.cargar(
        nombre_archivo="factura.pdf",
        tipo_contenido="application/pdf",
        contenido=b"%PDF-1.4 contenido de prueba",
        idioma=None,
        creado_por_id=1,
    )

    assert documento.estado == "pendiente"
    assert documento.nombre_archivo == "factura.pdf"
    assert documento.idioma == get_settings().tesseract_langs
    assert len(cola.tareas) == 1


async def test_cargar_documento_encola_una_tarea_que_procesa_ese_documento() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)

    documento = await service.cargar(
        nombre_archivo="foto.png",
        tipo_contenido="image/png",
        contenido=b"contenido-de-imagen",
        idioma=None,
        creado_por_id=1,
    )

    tarea = cola.tareas[0]
    await tarea()

    procesado = await repositorio.obtener(documento.id)
    assert procesado is not None
    assert procesado.estado == "procesado"


async def test_cargar_de_fuente_guarda_con_fuente_url_y_no_encola_nada() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)

    documento = await service.cargar_de_fuente(
        nombre_archivo="cauca-recauca.pdf",
        tipo_contenido="application/pdf",
        contenido=b"%PDF-1.4 contenido de prueba",
        idioma=None,
        creado_por_id=1,
        fuente_url="https://example.org/cauca.pdf",
    )

    assert documento.fuente_url == "https://example.org/cauca.pdf"
    assert documento.estado == "pendiente"
    assert cola.tareas == []


async def test_procesar_ahora_ejecuta_el_pipeline_en_el_proceso_actual() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)
    documento = await service.cargar_de_fuente(
        nombre_archivo="cauca-recauca.pdf",
        tipo_contenido="application/pdf",
        contenido=b"%PDF-1.4 contenido de prueba",
        idioma=None,
        creado_por_id=1,
        fuente_url="https://example.org/cauca.pdf",
    )

    await service.procesar_ahora(documento.id)

    procesado = await service.obtener(documento.id)
    assert procesado.estado == "procesado"


async def test_buscar_por_sha256_documento_existente_lo_devuelve() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)
    documento = await service.cargar(
        nombre_archivo="factura.pdf",
        tipo_contenido="application/pdf",
        contenido=b"contenido unico de esta factura",
        idioma=None,
        creado_por_id=1,
    )
    sha256 = hashlib.sha256(b"contenido unico de esta factura").hexdigest()

    encontrado = await service.buscar_por_sha256(sha256)

    assert encontrado is not None
    assert encontrado.id == documento.id


async def test_buscar_por_sha256_sin_coincidencias_devuelve_none() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)

    encontrado = await service.buscar_por_sha256("0" * 64)

    assert encontrado is None


def test_validar_carga_delega_en_el_validador() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)

    idioma = service.validar_carga("norma.pdf", "application/pdf", 1024, None)

    assert idioma == get_settings().tesseract_langs


async def test_listar_devuelve_los_documentos_paginados_y_el_total() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)
    for indice in range(3):
        await service.cargar(
            nombre_archivo=f"doc-{indice}.pdf",
            tipo_contenido="application/pdf",
            contenido=b"contenido",
            idioma=None,
            creado_por_id=1,
        )

    documentos, total = await service.listar(limite=2, offset=0)

    assert total == 3
    assert len(documentos) == 2
