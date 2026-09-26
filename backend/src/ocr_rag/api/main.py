"""Punto de entrada de la aplicación: arma la app, el `lifespan` y el middleware."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from ocr_rag.api.dependencies import (
    get_documento_repository,
    get_embedding_client,
    get_extractor_texto,
    get_ocr_client,
    get_procesamiento_service,
)
from ocr_rag.api.errors import registrar_manejadores_de_error
from ocr_rag.api.routers import auth, consultas, documentos, health, me
from ocr_rag.application.background import BackgroundTaskQueue, Tarea
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.core.settings import Settings, get_settings
from ocr_rag.infrastructure.db import ConnectionFactory

logger = logging.getLogger(__name__)

# Timeout explícito para las llamadas a OpenAI (embeddings y chat).
_TIMEOUT_OPENAI_SEGUNDOS = 60.0


def _configurar_logging() -> None:
    """Configura el logging estándar una única vez, al arrancar el proceso."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Abre los pools de conexión y la cola de tareas al arrancar; los cierra al apagar."""
    _configurar_logging()
    settings = get_settings()

    connection_factory = ConnectionFactory()
    await connection_factory.abrir("MAIN", settings.db_main_dsn.get_secret_value())
    app.state.connection_factory = connection_factory

    openai_client = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(), timeout=_TIMEOUT_OPENAI_SEGUNDOS
    )
    app.state.openai_client = openai_client

    tareas = BackgroundTaskQueue()
    await tareas.iniciar()
    app.state.tareas = tareas

    await _reencolar_documentos_sin_terminar(connection_factory, openai_client, settings, tareas)

    logger.info("OCR-RAG arrancó correctamente")
    try:
        yield
    finally:
        await tareas.detener()
        await connection_factory.cerrar_todos()
        logger.info("OCR-RAG se detuvo correctamente")


async def _reencolar_documentos_sin_terminar(
    connection_factory: ConnectionFactory,
    openai_client: AsyncOpenAI,
    settings: Settings,
    tareas: BackgroundTaskQueue,
) -> None:
    """Reencola el procesamiento de los documentos que quedaron `pendiente` o `procesando`.

    Un reinicio del proceso (deploy, caída) no debe dejarlos colgados: sin esto, quedarían en
    ese estado para siempre porque nadie vuelve a encolar su procesamiento.
    """
    repositorio = get_documento_repository(connection_factory)
    ocr_client = get_ocr_client()
    extractor = get_extractor_texto(ocr_client)
    embedding_client = get_embedding_client(openai_client, settings)
    procesamiento_service = get_procesamiento_service(repositorio, extractor, embedding_client)

    ids_pendientes = await repositorio.listar_ids_pendientes_o_procesando()
    for documento_id in ids_pendientes:
        await tareas.encolar(_crear_tarea_de_procesamiento(procesamiento_service, documento_id))
    if ids_pendientes:
        logger.info("Se reencolaron %s documentos sin terminar de procesar", len(ids_pendientes))


def _crear_tarea_de_procesamiento(
    procesamiento_service: ProcesamientoDocumentoService, documento_id: int
) -> Tarea:
    """Liga `documento_id` a la tarea en el momento de crearla (evita el late binding de un
    closure dentro del `for`).
    """

    async def _tarea() -> None:
        await procesamiento_service.procesar(documento_id)

    return _tarea


def crear_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title="OCR-RAG",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registrar_manejadores_de_error(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(documentos.router)
    app.include_router(consultas.router)

    return app


app = crear_app()
