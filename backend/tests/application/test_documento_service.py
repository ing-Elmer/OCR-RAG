"""Tests del `DocumentoService`."""

import hashlib

import pytest

from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.core.exceptions import NotFoundError
from ocr_rag.core.schemas.documento import DocumentoActualizacionRequest
from ocr_rag.core.settings import get_settings
from tests.conftest import (
    FakeBackgroundTaskQueue,
    FakeClasificadorDocumento,
    FakeDocumentoRepository,
    FakeEmbeddingClient,
    FakeExtractorTexto,
)


def _crear_service(
    repositorio: FakeDocumentoRepository,
    cola: FakeBackgroundTaskQueue,
    clasificador: FakeClasificadorDocumento | None = None,
) -> DocumentoService:
    procesador = ProcesamientoDocumentoService(
        repositorio,
        FakeExtractorTexto(),
        FakeEmbeddingClient(),
        clasificador or FakeClasificadorDocumento(),
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
        tipo_documento="normativa",
        norma="CAUCA IV",
    )

    assert documento.fuente_url == "https://example.org/cauca.pdf"
    assert documento.estado == "pendiente"
    assert documento.tipo_documento == "normativa"
    assert documento.norma == "CAUCA IV"
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
        tipo_documento="normativa",
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


async def test_cargar_sin_tipo_documento_lo_clasifica_al_procesar() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    clasificador = FakeClasificadorDocumento(tipo="aduanero")
    service = _crear_service(repositorio, cola, clasificador)

    documento = await service.cargar(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        contenido=b"contenido",
        idioma=None,
        creado_por_id=1,
    )
    assert documento.tipo_documento == "otro"

    await cola.tareas[0]()

    procesado = await repositorio.obtener(documento.id)
    assert procesado is not None
    assert procesado.tipo_documento == "aduanero"
    assert len(clasificador.llamadas) == 1


async def test_cargar_con_tipo_documento_no_llama_al_clasificador() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    clasificador = FakeClasificadorDocumento(tipo="aduanero")
    service = _crear_service(repositorio, cola, clasificador)

    documento = await service.cargar(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        contenido=b"contenido",
        idioma=None,
        creado_por_id=1,
        tipo_documento="contrato",
    )
    assert documento.tipo_documento == "contrato"

    await cola.tareas[0]()

    procesado = await repositorio.obtener(documento.id)
    assert procesado is not None
    assert procesado.tipo_documento == "contrato"
    assert clasificador.llamadas == []


async def test_actualizar_documento_inexistente_lanza_not_found() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)

    with pytest.raises(NotFoundError):
        await service.actualizar(
            999, DocumentoActualizacionRequest.model_validate({"tipoDocumento": "contrato"})
        )


async def test_actualizar_tipo_y_norma_los_actualiza_sin_reencolar() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)
    documento = await service.cargar_de_fuente(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        contenido=b"contenido",
        idioma=None,
        creado_por_id=1,
        fuente_url="https://example.org/a.pdf",
        tipo_documento="normativa",
        norma="CAUCA IV",
    )

    actualizado = await service.actualizar(
        documento.id, DocumentoActualizacionRequest.model_validate({"norma": "RECAUCA IV"})
    )

    assert actualizado.tipo_documento == "normativa"
    assert actualizado.norma == "RECAUCA IV"
    # El tipo no cambió (sigue siendo "normativa"): no hace falta reencolar el procesamiento.
    assert cola.tareas == []


async def test_actualizar_norma_null_la_limpia() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)
    documento = await service.cargar_de_fuente(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        contenido=b"contenido",
        idioma=None,
        creado_por_id=1,
        fuente_url="https://example.org/a.pdf",
        tipo_documento="normativa",
        norma="CAUCA IV",
    )

    actualizado = await service.actualizar(
        documento.id, DocumentoActualizacionRequest.model_validate({"norma": None})
    )

    assert actualizado.norma is None


async def test_actualizar_tipo_a_normativa_reencola_el_procesamiento() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)
    documento = await service.cargar(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        contenido=b"contenido",
        idioma=None,
        creado_por_id=1,
        tipo_documento="otro",
    )
    cola.tareas.clear()
    version_inicial = repositorio.version_de(documento.id)

    actualizado = await service.actualizar(
        documento.id, DocumentoActualizacionRequest.model_validate({"tipoDocumento": "normativa"})
    )

    assert len(cola.tareas) == 1
    # Sube la versión y deja el documento "pendiente" (aunque ya estuviera "procesado"), para
    # que el reprocesamiento que se acaba de encolar gane sobre cualquier resultado en vuelo.
    assert repositorio.version_de(documento.id) == version_inicial + 1
    assert repositorio.clasificacion_pendiente_de(documento.id) is False
    assert actualizado.estado == "pendiente"


async def test_actualizar_tipo_desde_normativa_reencola_el_procesamiento() -> None:
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)
    documento = await service.cargar_de_fuente(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        contenido=b"contenido",
        idioma=None,
        creado_por_id=1,
        fuente_url="https://example.org/a.pdf",
        tipo_documento="normativa",
    )
    version_inicial = repositorio.version_de(documento.id)

    await service.actualizar(
        documento.id, DocumentoActualizacionRequest.model_validate({"tipoDocumento": "contrato"})
    )

    assert len(cola.tareas) == 1
    assert repositorio.version_de(documento.id) == version_inicial + 1


async def test_actualizar_tipo_sin_pasar_por_normativa_no_reencola_pero_limpia_clasificacion_pendiente() -> (  # noqa: E501
    None
):
    repositorio = FakeDocumentoRepository()
    cola = FakeBackgroundTaskQueue()
    service = _crear_service(repositorio, cola)
    documento = await service.cargar(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        contenido=b"contenido",
        idioma=None,
        creado_por_id=1,
        tipo_documento="contrato",
    )
    cola.tareas.clear()
    version_inicial = repositorio.version_de(documento.id)

    await service.actualizar(
        documento.id, DocumentoActualizacionRequest.model_validate({"tipoDocumento": "aduanero"})
    )

    assert cola.tareas == []
    # No cruza la frontera de "normativa": no reencola ni sube la versión.
    assert repositorio.version_de(documento.id) == version_inicial
    # Pero una edición manual del tipo siempre limpia la clasificación pendiente.
    assert repositorio.clasificacion_pendiente_de(documento.id) is False
