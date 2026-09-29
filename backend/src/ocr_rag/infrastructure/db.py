"""Fábrica de pools de conexión a PostgreSQL, uno por nombre lógico."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# Ninguna sentencia corre sin límite de tiempo contra la base.
_STATEMENT_TIMEOUT_MS = "30000"


class ConnectionFactory:
    """Administra un `AsyncConnectionPool` por nombre lógico de conexión.

    Los pools se abren y se cierran desde el `lifespan` de la aplicación, nunca al importar
    este módulo.
    """

    def __init__(self) -> None:
        self._pools: dict[str, AsyncConnectionPool[AsyncConnection[Any]]] = {}

    async def abrir(self, nombre: str, dsn: str, *, solo_lectura: bool = False) -> None:
        """Abre el pool de conexiones `nombre`.

        Las conexiones marcadas como solo lectura en el perfil del proyecto deben abrirse con
        `solo_lectura=True` y nunca reciben `INSERT`/`UPDATE`/`DELETE`.
        """
        opciones = f"-c statement_timeout={_STATEMENT_TIMEOUT_MS}"
        if solo_lectura:
            opciones += " -c default_transaction_read_only=on"
        pool: AsyncConnectionPool[AsyncConnection[Any]] = AsyncConnectionPool(
            conninfo=dsn,
            kwargs={"options": opciones},
            open=False,
        )
        await pool.open(wait=True)
        self._pools[nombre] = pool
        logger.info("Pool de conexiones '%s' abierto", nombre)

    async def cerrar_todos(self) -> None:
        """Cierra todos los pools abiertos. Se llama al apagar la aplicación."""
        for nombre, pool in self._pools.items():
            await pool.close()
            logger.info("Pool de conexiones '%s' cerrado", nombre)
        self._pools.clear()

    @asynccontextmanager
    async def connection(self, nombre: str) -> AsyncIterator[AsyncConnection[Any]]:
        """Entrega, como context manager async, una conexión del pool `nombre`."""
        pool = self._pools.get(nombre)
        if pool is None:
            raise RuntimeError(f"No hay un pool de conexiones abierto con el nombre '{nombre}'")
        async with pool.connection() as conn:
            yield conn
