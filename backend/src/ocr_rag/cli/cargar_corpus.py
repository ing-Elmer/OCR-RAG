"""Comando `cargar-corpus`: carga masiva del corpus normativo desde un manifiesto TOML.

Arma sus propias dependencias (como `crear_admin.py`) porque no hay un proceso ASGI que las
arme por él: abre la `ConnectionFactory` y el cliente de OpenAI, y los cierra al salir. No
encola nada en background: procesa cada fuente (descarga, valida, carga, OCR + embeddings) en
el mismo proceso, de a una, para que el progreso y los errores sean claros en la consola.
"""

import argparse
import asyncio
import importlib.resources
import sys
import tomllib
from pathlib import Path

from openai import AsyncOpenAI

from ocr_rag.application.background import BackgroundTaskQueue
from ocr_rag.application.services.corpus_service import CorpusService, ResultadoCargaFuente
from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.core.repositories import UsuarioRepository
from ocr_rag.core.schemas.corpus import FuenteCorpus, ManifiestoCorpus
from ocr_rag.core.schemas.usuario import UsuarioCredenciales
from ocr_rag.core.settings import get_settings
from ocr_rag.infrastructure.clients.http_descargador_client import UrllibDescargadorHttp
from ocr_rag.infrastructure.clients.openai_clasificador_documento_client import (
    OpenAiClasificadorDocumentoClient,
)
from ocr_rag.infrastructure.clients.openai_embedding_client import OpenAiEmbeddingClient
from ocr_rag.infrastructure.clients.pdf_ocr_extractor_client import PdfOcrExtractorClient
from ocr_rag.infrastructure.clients.tesseract_ocr_client import TesseractOcrClient
from ocr_rag.infrastructure.db import ConnectionFactory
from ocr_rag.infrastructure.repositories.documento_repository import PostgresDocumentoRepository
from ocr_rag.infrastructure.repositories.usuario_repository import PostgresUsuarioRepository

# Timeout explícito para las llamadas a OpenAI (embeddings), igual que en el `lifespan` de la API.
_TIMEOUT_OPENAI_SEGUNDOS = 60.0


def _parsear_argumentos(argv: list[str]) -> argparse.Namespace:
    """Define y parsea los argumentos del comando `cargar-corpus`."""
    parser = argparse.ArgumentParser(
        prog="python -m ocr_rag.cli cargar-corpus",
        description=(
            "Carga masiva del corpus normativo desde un manifiesto TOML: por cada fuente, "
            "descarga el PDF, lo valida, lo carga y lo procesa (OCR + embeddings) en el mismo "
            "proceso. Un error en una fuente no detiene la carga de las demás."
        ),
    )
    parser.add_argument(
        "--usuario",
        required=True,
        help="Username de un usuario existente y activo; queda como 'creado_por' de los "
        "documentos cargados.",
    )
    parser.add_argument(
        "--manifiesto",
        type=Path,
        default=None,
        help="Ruta a un manifiesto TOML alternativo. Por defecto usa el manifiesto empaquetado "
        "'normativa_centroamerica.toml'.",
    )
    parser.add_argument(
        "--solo",
        default=None,
        help="Lista de ids de fuente separados por coma (por defecto, carga todas las del "
        "manifiesto).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Descarga y valida cada fuente, e informa qué haría, sin escribir en la base ni "
        "llamar a OpenAI.",
    )
    return parser.parse_args(argv)


def _leer_manifiesto_por_defecto() -> str:
    """Texto del manifiesto empaquetado dentro del paquete `ocr_rag.cli.corpus`."""
    recurso = importlib.resources.files("ocr_rag.cli.corpus").joinpath(
        "normativa_centroamerica.toml"
    )
    return recurso.read_text(encoding="utf-8")


def cargar_manifiesto(ruta: Path | None) -> ManifiestoCorpus:
    """Lee y valida el manifiesto de `ruta`, o el empaquetado por defecto si `ruta` es `None`."""
    texto = _leer_manifiesto_por_defecto() if ruta is None else ruta.read_text(encoding="utf-8")
    datos = tomllib.loads(texto)
    return ManifiestoCorpus.model_validate(datos)


def resolver_fuentes(manifiesto: ManifiestoCorpus, solo: str | None) -> list[FuenteCorpus] | None:
    """Filtra las fuentes del manifiesto según `--solo`.

    Devuelve `None` (en lugar de lanzar) si `solo` pide algún id que no existe en el
    manifiesto, para que el caller pueda reportar el error e interrumpir con exit 1.
    """
    if not solo:
        return list(manifiesto.fuente)

    ids_pedidos = {id_.strip() for id_ in solo.split(",") if id_.strip()}
    ids_disponibles = {fuente.id for fuente in manifiesto.fuente}
    ids_invalidos = ids_pedidos - ids_disponibles
    if ids_invalidos:
        ids_listados = ", ".join(sorted(ids_invalidos))
        print(f"Error: --solo pide ids que no existen en el manifiesto: {ids_listados}")
        return None
    return [fuente for fuente in manifiesto.fuente if fuente.id in ids_pedidos]


async def resolver_usuario(
    username: str, usuario_repositorio: UsuarioRepository
) -> UsuarioCredenciales | None:
    """Busca el usuario activo `username`. Imprime un error y devuelve `None` si no existe."""
    credenciales = await usuario_repositorio.obtener_credenciales_activas(username)
    if credenciales is None:
        print(f"Error: no existe un usuario activo con username '{username}'")
    return credenciales


async def ejecutar_carga(
    fuentes: list[FuenteCorpus],
    creado_por_id: int,
    corpus_service: CorpusService,
    *,
    dry_run: bool,
) -> int:
    """Carga cada fuente, imprime el progreso y el resumen final, y devuelve el exit code.

    Un error en una fuente no detiene la carga de las demás. Exit 0 si ninguna falló, 1 si al
    menos una terminó en estado `error`.
    """
    total = len(fuentes)
    cargadas = omitidas = con_error = 0
    for indice, fuente in enumerate(fuentes, start=1):
        print(f"[{indice}/{total}] {fuente.id} … descargando", flush=True)
        resultado = await corpus_service.cargar_fuente(fuente, creado_por_id, dry_run=dry_run)
        cargadas, omitidas, con_error = _acumular_e_informar(
            resultado, cargadas, omitidas, con_error
        )

    print(
        f"Resumen: {cargadas} cargadas, {omitidas} omitidas, {con_error} con error "
        f"(de {total} fuentes)."
    )
    return 1 if con_error else 0


def _acumular_e_informar(
    resultado: ResultadoCargaFuente, cargadas: int, omitidas: int, con_error: int
) -> tuple[int, int, int]:
    """Imprime el resultado de una fuente y devuelve los contadores actualizados."""
    if resultado.estado == "cargado":
        print(f"    OK: {resultado.detalle}")
        return cargadas + 1, omitidas, con_error
    if resultado.estado == "omitido":
        print(f"    Omitido: {resultado.detalle}")
        return cargadas, omitidas + 1, con_error
    print(f"    Error: {resultado.detalle}")
    return cargadas, omitidas, con_error + 1


async def _cargar_corpus(argv: list[str]) -> int:
    """Arma las dependencias contra la base configurada en `Settings` y ejecuta la carga."""
    args = _parsear_argumentos(argv)
    manifiesto = cargar_manifiesto(args.manifiesto)
    fuentes = resolver_fuentes(manifiesto, args.solo)
    if fuentes is None:
        return 1

    settings = get_settings()
    connection_factory = ConnectionFactory()
    await connection_factory.abrir("MAIN", settings.db_main_dsn.get_secret_value())
    openai_client = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(), timeout=_TIMEOUT_OPENAI_SEGUNDOS
    )
    try:
        usuario_repositorio = PostgresUsuarioRepository(connection_factory)
        credenciales = await resolver_usuario(args.usuario, usuario_repositorio)
        if credenciales is None:
            return 1

        documento_repositorio = PostgresDocumentoRepository(connection_factory)
        validador = DocumentoValidator(documento_repositorio, settings)
        procesador = ProcesamientoDocumentoService(
            documento_repositorio,
            PdfOcrExtractorClient(TesseractOcrClient()),
            OpenAiEmbeddingClient(openai_client, settings.openai_embedding_model),
            # El manifiesto siempre trae `tipo`, así que la carga masiva nunca clasifica: este
            # cliente solo existe para satisfacer el constructor del worker.
            OpenAiClasificadorDocumentoClient(openai_client, settings.openai_chat_model),
        )
        # `BackgroundTaskQueue` sin `iniciar()`: el CLI no tiene worker, así que `cargar_de_fuente`
        # + `procesar_ahora` nunca la usan; la exige el constructor de `DocumentoService`.
        documento_service = DocumentoService(
            documento_repositorio, validador, procesador, BackgroundTaskQueue()
        )
        corpus_service = CorpusService(documento_service, UrllibDescargadorHttp(), settings)

        return await ejecutar_carga(fuentes, credenciales.id, corpus_service, dry_run=args.dry_run)
    finally:
        await connection_factory.cerrar_todos()


def main() -> None:
    """Punto de entrada síncrono del comando `cargar-corpus`.

    En Windows, `psycopg` async requiere un `SelectorEventLoop`: el `ProactorEventLoop` (el
    default) no soporta los sockets que usa `psycopg_pool`.
    """
    codigo = asyncio.run(_cargar_corpus(sys.argv[2:]), loop_factory=asyncio.SelectorEventLoop)
    raise SystemExit(codigo)
