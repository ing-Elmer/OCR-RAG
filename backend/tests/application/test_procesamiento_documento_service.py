"""Tests del `ProcesamientoDocumentoService` (worker de OCR + embeddings)."""

from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.core.schemas.documento import PaginaExtraida
from tests.conftest import FakeDocumentoRepository, FakeEmbeddingClient, FakeExtractorTexto


async def _crear_documento_pendiente(repositorio: FakeDocumentoRepository) -> int:
    return await repositorio.crear(
        nombre_archivo="documento.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=100,
        idioma="spa",
        creado_por_id=1,
        contenido=b"%PDF-1.4 contenido de prueba",
        sha256="a" * 64,
    )


async def test_procesar_documento_ok_queda_procesado_con_chunks_en_orden() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas = [
        PaginaExtraida(numero=1, texto="Primera oración de la página uno. " * 20),
        PaginaExtraida(numero=2, texto="Primera oración de la página dos. " * 20),
    ]
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(paginas), FakeEmbeddingClient()
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "procesado"
    assert documento.paginas == 2
    assert documento.cantidad_chunks > 0

    chunks = repositorio.chunks_de(documento_id)
    ordenes = [chunk.orden for chunk in chunks]
    assert ordenes == sorted(ordenes)
    assert ordenes == list(range(len(chunks)))
    for chunk in chunks:
        assert chunk.embedding


async def test_procesar_documento_sin_texto_extraible_queda_en_error() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas_vacias = [PaginaExtraida(numero=1, texto="   ")]
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(paginas_vacias), FakeEmbeddingClient()
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "error"
    assert documento.error_detalle == "No se pudo extraer texto del documento"


async def test_procesar_documento_falla_de_embeddings_queda_en_error_generico() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas = [PaginaExtraida(numero=1, texto="Texto suficiente para generar un chunk. " * 10)]
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(paginas), FakeEmbeddingClient(falla=True)
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "error"
    assert documento.error_detalle == "No se pudo procesar el documento"
    # El mensaje expuesto es genérico: nunca el detalle técnico de la excepción real.
    assert "OpenAI" not in (documento.error_detalle or "")


async def test_procesar_documento_dos_veces_es_idempotente_no_duplica_chunks() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas = [PaginaExtraida(numero=1, texto="Contenido de prueba para el chunking. " * 20)]
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(paginas), FakeEmbeddingClient()
    )

    await service.procesar(documento_id)
    cantidad_primera_vez = len(repositorio.chunks_de(documento_id))

    await service.procesar(documento_id)
    cantidad_segunda_vez = len(repositorio.chunks_de(documento_id))

    assert cantidad_primera_vez > 0
    assert cantidad_segunda_vez == cantidad_primera_vez


async def test_procesar_documento_inexistente_no_lanza() -> None:
    repositorio = FakeDocumentoRepository()
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient()
    )

    # No debe lanzar ni intentar marcar estados sobre un documento que ya no existe.
    await service.procesar(999)
