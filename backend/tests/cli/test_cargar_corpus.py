"""Tests de las piezas puras de `cli cargar-corpus`: sin red, sin base real, con fakes."""

from datetime import date

from ocr_rag.application.services.corpus_service import CorpusService
from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.cli.cargar_corpus import ejecutar_carga, resolver_fuentes, resolver_usuario
from ocr_rag.core.exceptions import DescargaInvalidaError
from ocr_rag.core.schemas.corpus import FuenteCorpus, ManifiestoCorpus
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales
from ocr_rag.core.settings import get_settings
from tests.conftest import (
    FakeBackgroundTaskQueue,
    FakeClasificadorDocumento,
    FakeDescargadorHttp,
    FakeDocumentoRepository,
    FakeEmbeddingClient,
    FakeExtractorTexto,
    FakeUsuarioRepository,
)


def _fuente(**overrides: object) -> FuenteCorpus:
    base: dict[str, object] = {
        "id": "cauca-recauca",
        "titulo": "Título de prueba",
        "url": "https://example.org/norma.pdf",
        "verificado": date(2026, 9, 26),
    }
    base.update(overrides)
    return FuenteCorpus.model_validate(base)


def _crear_corpus_service(
    repositorio: FakeDocumentoRepository, descargador: FakeDescargadorHttp
) -> CorpusService:
    validador = DocumentoValidator(repositorio, get_settings())
    procesador = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient(), FakeClasificadorDocumento()
    )
    documento_service = DocumentoService(
        repositorio, validador, procesador, FakeBackgroundTaskQueue()
    )
    return CorpusService(documento_service, descargador, get_settings())


async def test_resolver_usuario_inexistente_imprime_error_y_devuelve_none() -> None:
    repositorio = FakeUsuarioRepository()

    credenciales = await resolver_usuario("no-existe", repositorio)

    assert credenciales is None


async def test_resolver_usuario_activo_devuelve_sus_credenciales() -> None:
    usuario = CurrentUserResponse(
        id=1, username="ana", nombre_completo="Ana Pérez", roles=[], permisos=[]
    )
    credenciales_ana = UsuarioCredenciales(id=1, username="ana", password_hash="hash")
    repositorio = FakeUsuarioRepository({1: usuario}, {"ana": credenciales_ana})

    credenciales = await resolver_usuario("ana", repositorio)

    assert credenciales is not None
    assert credenciales.username == "ana"


def test_resolver_fuentes_sin_solo_devuelve_todas() -> None:
    manifiesto = ManifiestoCorpus(fuente=[_fuente(id="a"), _fuente(id="b")])

    fuentes = resolver_fuentes(manifiesto, None)

    assert fuentes is not None
    assert [f.id for f in fuentes] == ["a", "b"]


def test_resolver_fuentes_con_solo_filtra_por_id() -> None:
    manifiesto = ManifiestoCorpus(fuente=[_fuente(id="a"), _fuente(id="b")])

    fuentes = resolver_fuentes(manifiesto, "b")

    assert fuentes is not None
    assert [f.id for f in fuentes] == ["b"]


def test_resolver_fuentes_con_id_desconocido_devuelve_none() -> None:
    manifiesto = ManifiestoCorpus(fuente=[_fuente(id="a")])

    fuentes = resolver_fuentes(manifiesto, "no-existe")

    assert fuentes is None


async def test_ejecutar_carga_un_fallo_no_detiene_las_siguientes_y_exit_code_es_1() -> None:
    repositorio = FakeDocumentoRepository()
    descargador = FakeDescargadorHttp()
    fuente_falla = _fuente(id="falla", url="https://example.org/falla.pdf")
    fuente_ok = _fuente(id="ok", url="https://example.org/ok.pdf")
    descargador.fallos[fuente_falla.url] = DescargaInvalidaError("no se pudo descargar")
    corpus_service = _crear_corpus_service(repositorio, descargador)

    codigo = await ejecutar_carga(
        [fuente_falla, fuente_ok], creado_por_id=1, corpus_service=corpus_service, dry_run=False
    )

    assert codigo == 1
    _documentos, total = await repositorio.listar(limite=10, offset=0)
    assert total == 1  # la fuente "ok" se cargó igual


async def test_ejecutar_carga_sin_errores_devuelve_exit_code_0() -> None:
    repositorio = FakeDocumentoRepository()
    descargador = FakeDescargadorHttp()
    corpus_service = _crear_corpus_service(repositorio, descargador)

    codigo = await ejecutar_carga(
        [_fuente()], creado_por_id=1, corpus_service=corpus_service, dry_run=False
    )

    assert codigo == 0
