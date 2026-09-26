"""Repositorio de salud: verifica la conexión principal a la base."""

from ocr_rag.infrastructure.db import ConnectionFactory


class PostgresHealthRepository:
    """Implementación de `HealthRepository` (`core.repositories`) sobre PostgreSQL."""

    def __init__(self, db: ConnectionFactory) -> None:
        self._db = db

    async def verificar_conexion(self) -> bool:
        """Ejecuta un `SELECT 1` contra la conexión principal `MAIN`."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1")
            fila = await cur.fetchone()
            return fila is not None and fila[0] == 1
