"""Tests de las piezas puras de `cli reprocesar`: sin red, sin base real, con fakes."""

from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.cli.reprocesar import (
    ejecutar_reprocesamiento,
    parsear_ids,
    resolver_documentos_por_id,
    resolver_documentos_todos,
)
from ocr_rag.core.clients import ExtractorTexto
from ocr_rag.core.schemas.documento import PaginaExtraida
from ocr_rag.core.settings import get_settings
from tests.conftest import (
    FakeBackgroundTaskQueue,
    FakeClasificadorDocumento,
    FakeDocumentoRepository,
    FakeEmbeddingClient,
    FakeExtractorTexto,
)


class _ExtractorCondicional:
    """Extractor de texto fake que devuelve páginas sin texto solo para `contenido_sin_texto`,
    para poder simular que un documento en particular falla al reprocesarse sin que afecte a
    los demás.
    """

    def __init__(self, contenido_sin_texto: bytes) -> None:
        self._contenido_sin_texto = contenido_sin_texto

    async def extraer(
        self, contenido: bytes, tipo_contenido: str, idioma: str
    ) -> list[PaginaExtraida]:
        if contenido == self._contenido_sin_texto:
            return [PaginaExtraida(numero=1, texto="   ")]
        return [PaginaExtraida(numero=1, texto="Hola mundo. " * 20)]


def _crear_documento_service(
    repositorio: FakeDocumentoRepository,
    *,
    extractor: ExtractorTexto | None = None,
    clasificador: FakeClasificadorDocumento | None = None,
) -> tuple[DocumentoService, FakeClasificadorDocumento]:
    clasificador = clasificador or FakeClasificadorDocumento()
    validador = DocumentoValidator(repositorio, get_settings())
    procesador = ProcesamientoDocumentoService(
        repositorio, extractor or FakeExtractorTexto(), FakeEmbeddingClient(), clasificador
    )
    documento_service = DocumentoService(
        repositorio, validador, procesador, FakeBackgroundTaskQueue()
    )
    return documento_service, clasificador


async def _crear_documento(
    repositorio: FakeDocumentoRepository, *, nombre_archivo: str = "norma.pdf"
) -> int:
    return await repositorio.crear(
        nombre_archivo=nombre_archivo,
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256=f"sha-{nombre_archivo}",
    )


# --- parsear_ids -------------------------------------------------------------------------


def test_parsear_ids_admite_un_solo_id() -> None:
    assert parsear_ids("7") == [7]


def test_parsear_ids_admite_varios_ids_separados_por_coma() -> None:
    assert parsear_ids("3, 7,12") == [3, 7, 12]


def test_parsear_ids_con_valor_no_numerico_devuelve_none() -> None:
    assert parsear_ids("3,abc,12") is None


def test_parsear_ids_vacio_devuelve_none() -> None:
    assert parsear_ids("  ,  ") is None


# --- resolver_documentos_todos -----------------------------------------------------------


async def test_resolver_documentos_todos_omite_pendientes_y_procesando() -> None:
    repositorio = FakeDocumentoRepository()
    documento_service, _ = _crear_documento_service(repositorio)
    id_pendiente = await _crear_documento(repositorio, nombre_archivo="pendiente.pdf")
    id_procesando = await _crear_documento(repositorio, nombre_archivo="procesando.pdf")
    id_procesado = await _crear_documento(repositorio, nombre_archivo="procesado.pdf")
    id_error = await _crear_documento(repositorio, nombre_archivo="error.pdf")
    await repositorio.tomar_para_procesar(id_procesando)
    tomado_procesado = await repositorio.tomar_para_procesar(id_procesado)
    assert tomado_procesado is not None
    await repositorio.guardar_resultado(id_procesado, 1, [], tomado_procesado.version_procesamiento)
    tomado_error = await repositorio.tomar_para_procesar(id_error)
    assert tomado_error is not None
    await repositorio.marcar_error(id_error, "falló", tomado_error.version_procesamiento)

    documentos = await resolver_documentos_todos(documento_service)

    ids_resultado = {documento.id for documento in documentos}
    assert ids_resultado == {id_procesado, id_error}
    assert id_pendiente not in ids_resultado
    assert id_procesando not in ids_resultado


# --- resolver_documentos_por_id ------------------------------------------------------------


async def test_resolver_documentos_por_id_con_id_inexistente_devuelve_none() -> None:
    repositorio = FakeDocumentoRepository()
    documento_service, _ = _crear_documento_service(repositorio)
    id_existente = await _crear_documento(repositorio)

    documentos = await resolver_documentos_por_id(documento_service, [id_existente, 999])

    assert documentos is None


async def test_resolver_documentos_por_id_con_ids_existentes_los_devuelve_en_orden() -> None:
    repositorio = FakeDocumentoRepository()
    documento_service, _ = _crear_documento_service(repositorio)
    primero = await _crear_documento(repositorio, nombre_archivo="a.pdf")
    segundo = await _crear_documento(repositorio, nombre_archivo="b.pdf")

    documentos = await resolver_documentos_por_id(documento_service, [segundo, primero])

    assert documentos is not None
    assert [documento.id for documento in documentos] == [segundo, primero]


# --- ejecutar_reprocesamiento --------------------------------------------------------------


async def test_ejecutar_reprocesamiento_un_fallo_no_detiene_los_demas_y_exit_code_es_1() -> None:
    repositorio = FakeDocumentoRepository()
    contenido_falla = b"contenido-sin-texto"
    documento_service, _ = _crear_documento_service(
        repositorio, extractor=_ExtractorCondicional(contenido_falla)
    )
    id_falla = await repositorio.crear(
        nombre_archivo="falla.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=contenido_falla,
        sha256="sha-falla",
    )
    id_ok = await _crear_documento(repositorio, nombre_archivo="ok.pdf")
    documento_falla = await repositorio.obtener(id_falla)
    documento_ok = await repositorio.obtener(id_ok)
    assert documento_falla is not None and documento_ok is not None

    codigo = await ejecutar_reprocesamiento([documento_falla, documento_ok], documento_service)

    assert codigo == 1
    resultado_falla = await repositorio.obtener(id_falla)
    resultado_ok = await repositorio.obtener(id_ok)
    assert resultado_falla is not None and resultado_falla.estado == "error"
    assert resultado_ok is not None and resultado_ok.estado == "procesado"


async def test_ejecutar_reprocesamiento_sin_errores_devuelve_exit_code_0() -> None:
    repositorio = FakeDocumentoRepository()
    documento_service, _ = _crear_documento_service(repositorio)
    id_documento = await _crear_documento(repositorio)
    documento = await repositorio.obtener(id_documento)
    assert documento is not None

    codigo = await ejecutar_reprocesamiento([documento], documento_service)

    assert codigo == 0
    resultado = await repositorio.obtener(id_documento)
    assert resultado is not None and resultado.estado == "procesado"


async def test_ejecutar_reprocesamiento_con_tipo_ya_resuelto_no_reclasifica() -> None:
    """Un documento cuyo tipo ya se resolvió (indicado en la carga, clasificado, o editado
    manualmente) conserva ese tipo: `clasificacion_pendiente` es `False`, así que el
    reprocesamiento no vuelve a llamar al clasificador.
    """
    repositorio = FakeDocumentoRepository()
    clasificador = FakeClasificadorDocumento(tipo="embarque")
    documento_service, clasificador = _crear_documento_service(
        repositorio, clasificador=clasificador
    )
    id_documento = await repositorio.crear(
        nombre_archivo="norma.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256="sha-norma",
        tipo_documento="normativa",
    )
    documento = await repositorio.obtener(id_documento)
    assert documento is not None

    await ejecutar_reprocesamiento([documento], documento_service)

    assert clasificador.llamadas == []
    resultado = await repositorio.obtener(id_documento)
    assert resultado is not None and resultado.tipo_documento == "normativa"


async def test_ejecutar_reprocesamiento_con_clasificacion_pendiente_la_completa() -> None:
    """Un documento cargado sin tipo cuyo primer intento falló antes de clasificar (por eso
    `clasificacion_pendiente` seguía en `True`) se clasifica al reprocesarlo.
    """
    repositorio = FakeDocumentoRepository()
    clasificador = FakeClasificadorDocumento(tipo="embarque")
    documento_service, clasificador = _crear_documento_service(
        repositorio, clasificador=clasificador
    )
    id_documento = await repositorio.crear(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256="sha-pendiente",
        clasificacion_pendiente=True,
    )
    documento = await repositorio.obtener(id_documento)
    assert documento is not None

    await ejecutar_reprocesamiento([documento], documento_service)

    assert len(clasificador.llamadas) == 1
    resultado = await repositorio.obtener(id_documento)
    assert resultado is not None and resultado.tipo_documento == "embarque"


async def test_ejecutar_reprocesamiento_documento_en_proceso_lo_omite_sin_exit_1() -> None:
    repositorio = FakeDocumentoRepository()
    documento_service, _ = _crear_documento_service(repositorio)
    id_documento = await _crear_documento(repositorio)
    await repositorio.tomar_para_procesar(id_documento)  # simula que el worker ya lo tomó
    documento = await repositorio.obtener(id_documento)
    assert documento is not None

    codigo = await ejecutar_reprocesamiento([documento], documento_service)

    assert codigo == 0
    resultado = await repositorio.obtener(id_documento)
    assert resultado is not None and resultado.estado == "procesando"
