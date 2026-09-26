"""Punto de entrada de la aplicación: arma la app, el `lifespan` y el middleware."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ocr_rag.api.errors import registrar_manejadores_de_error
from ocr_rag.api.routers import auth, health, me
from ocr_rag.application.background import BackgroundTaskQueue
from ocr_rag.core.settings import get_settings
from ocr_rag.infrastructure.db import ConnectionFactory

logger = logging.getLogger(__name__)


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

    tareas = BackgroundTaskQueue()
    await tareas.iniciar()
    app.state.tareas = tareas

    logger.info("OCR-RAG arrancó correctamente")
    try:
        yield
    finally:
        await tareas.detener()
        await connection_factory.cerrar_todos()
        logger.info("OCR-RAG se detuvo correctamente")


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

    return app


app = crear_app()
