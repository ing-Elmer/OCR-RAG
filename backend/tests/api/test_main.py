"""Tests de la recuperación de documentos sin terminar al arrancar (`api/main.py`)."""

from ocr_rag.api.main import _resetear_y_reencolar_pendientes
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from tests.conftest import (
    FakeBackgroundTaskQueue,
    FakeClasificadorDocumento,
    FakeDocumentoRepository,
    FakeEmbeddingClient,
    FakeExtractorTexto,
)


async def _crear_documento(
    repositorio: FakeDocumentoRepository,
    *,
    nombre_archivo: str,
    clasificacion_pendiente: bool = False,
) -> int:
    return await repositorio.crear(
        nombre_archivo=nombre_archivo,
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256=f"sha-{nombre_archivo}",
        clasificacion_pendiente=clasificacion_pendiente,
    )


async def test_resetear_y_reencolar_pendientes_devuelve_los_procesando_a_pendiente_y_reencola() -> (
    None
):
    repositorio = FakeDocumentoRepository()
    id_pendiente = await _crear_documento(repositorio, nombre_archivo="pendiente.pdf")
    id_procesando = await _crear_documento(repositorio, nombre_archivo="procesando.pdf")
    await repositorio.tomar_para_procesar(id_procesando)  # simula el corte por el reinicio
    id_procesado = await _crear_documento(repositorio, nombre_archivo="procesado.pdf")
    tomado = await repositorio.tomar_para_procesar(id_procesado)
    assert tomado is not None
    await repositorio.guardar_resultado(id_procesado, 1, [], tomado.version_procesamiento)

    procesamiento_service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient(), FakeClasificadorDocumento()
    )
    tareas = FakeBackgroundTaskQueue()

    await _resetear_y_reencolar_pendientes(repositorio, procesamiento_service, tareas)

    reseteado = await repositorio.obtener(id_procesando)
    assert reseteado is not None
    assert reseteado.estado == "pendiente"
    # Solo reencola los que quedan "pendiente" (el "procesando" recién reseteado, y el que ya
    # lo estaba); el "procesado" no se toca.
    assert len(tareas.tareas) == 2

    for tarea in tareas.tareas:
        await tarea()

    doc_pendiente_final = await repositorio.obtener(id_pendiente)
    doc_procesando_final = await repositorio.obtener(id_procesando)
    assert doc_pendiente_final is not None and doc_pendiente_final.estado == "procesado"
    assert doc_procesando_final is not None and doc_procesando_final.estado == "procesado"


async def test_resetear_y_reencolar_pendientes_clasifica_clasificacion_pendiente() -> None:
    """La intención de clasificar automáticamente un documento cargado sin `tipoDocumento` vive
    en la base (`clasificacion_pendiente`), no en el closure de la tarea: un reinicio no debe
    perderla.
    """
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento(
        repositorio, nombre_archivo="sin-tipo.pdf", clasificacion_pendiente=True
    )
    clasificador = FakeClasificadorDocumento(tipo="aduanero")
    procesamiento_service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient(), clasificador
    )
    tareas = FakeBackgroundTaskQueue()

    await _resetear_y_reencolar_pendientes(repositorio, procesamiento_service, tareas)
    for tarea in tareas.tareas:
        await tarea()

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.tipo_documento == "aduanero"
    assert documento.estado == "procesado"
    assert len(clasificador.llamadas) == 1


async def test_resetear_y_reencolar_pendientes_sin_nada_sin_terminar_no_encola_nada() -> None:
    repositorio = FakeDocumentoRepository()
    procesamiento_service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient(), FakeClasificadorDocumento()
    )
    tareas = FakeBackgroundTaskQueue()

    await _resetear_y_reencolar_pendientes(repositorio, procesamiento_service, tareas)

    assert tareas.tareas == []
