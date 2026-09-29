"""Cola de tareas en background sobre `asyncio.Queue`.

Pensada para trabajo lento y no bloqueante (por ejemplo, el procesamiento OCR de un
documento recién subido), que nunca debe correr dentro del ciclo de un request HTTP.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress

logger = logging.getLogger(__name__)

Tarea = Callable[[], Awaitable[None]]


class BackgroundTaskQueue:
    """Cola de tareas asíncronas con un único worker.

    El worker se arranca y se detiene desde el `lifespan` de la aplicación.
    """

    def __init__(self) -> None:
        self._cola: asyncio.Queue[Tarea] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None

    async def iniciar(self) -> None:
        """Arranca el worker que consume la cola."""
        self._worker = asyncio.create_task(self._consumir())

    async def detener(self) -> None:
        """Cancela el worker y espera a que termine de forma prolija."""
        if self._worker is None:
            return
        self._worker.cancel()
        with suppress(asyncio.CancelledError):
            await self._worker
        self._worker = None

    async def encolar(self, tarea: Tarea) -> None:
        """Agrega una tarea (por ejemplo, procesar el OCR de un documento) a la cola."""
        await self._cola.put(tarea)

    async def _consumir(self) -> None:
        """Ejecuta las tareas de la cola una a una; una tarea fallida no detiene al worker."""
        while True:
            tarea = await self._cola.get()
            try:
                await tarea()
            except Exception:
                logger.exception("Falló una tarea en segundo plano")
            finally:
                self._cola.task_done()
