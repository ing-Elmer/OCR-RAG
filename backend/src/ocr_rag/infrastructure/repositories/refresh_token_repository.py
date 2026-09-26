"""Repositorio de refresh tokens: emisión, rotación y revocación en PostgreSQL."""

import datetime as dt

from psycopg.rows import class_row

from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.infrastructure.db import ConnectionFactory

_SQL_CREAR = """
    INSERT INTO ocr_rag.ocr_refresh_token (usuario_id, token_hash, expires_at)
    VALUES (%(usuario_id)s, %(token_hash)s, %(expires_at)s)
    RETURNING id, usuario_id, token_hash, expires_at, revoked_at
"""

_SQL_OBTENER_POR_HASH = """
    SELECT id, usuario_id, token_hash, expires_at, revoked_at
      FROM ocr_rag.ocr_refresh_token
     WHERE token_hash = %(token_hash)s
"""

_SQL_REVOCAR_POR_HASH = """
    UPDATE ocr_rag.ocr_refresh_token
       SET revoked_at = now()
     WHERE token_hash = %(token_hash)s
       AND revoked_at IS NULL
"""

_SQL_REVOCAR_SI_VIGENTE = """
    UPDATE ocr_rag.ocr_refresh_token
       SET revoked_at = now()
     WHERE token_hash = %(token_hash)s
       AND revoked_at IS NULL
    RETURNING id
"""

_SQL_REVOCAR_TODOS_DE_USUARIO = """
    UPDATE ocr_rag.ocr_refresh_token
       SET revoked_at = now()
     WHERE usuario_id = %(usuario_id)s
       AND revoked_at IS NULL
"""


class PostgresRefreshTokenRepository:
    """Implementación de `RefreshTokenRepository` (`core.repositories`) sobre PostgreSQL."""

    def __init__(self, db: ConnectionFactory) -> None:
        self._db = db

    async def crear(
        self, usuario_id: int, token_hash: str, expires_at: dt.datetime
    ) -> RefreshTokenRegistro:
        """Crea un refresh token nuevo para el usuario y lo devuelve."""
        row_factory = class_row(RefreshTokenRegistro)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(
                _SQL_CREAR,
                {"usuario_id": usuario_id, "token_hash": token_hash, "expires_at": expires_at},
            )
            fila = await cur.fetchone()
        if fila is None:
            raise RuntimeError("El INSERT de ocr_refresh_token no devolvió la fila creada")
        return fila

    async def obtener_por_hash(self, token_hash: str) -> RefreshTokenRegistro | None:
        """Busca un refresh token por su hash, esté vigente o revocado."""
        row_factory = class_row(RefreshTokenRegistro)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(_SQL_OBTENER_POR_HASH, {"token_hash": token_hash})
            return await cur.fetchone()

    async def rotar(
        self,
        token_hash_actual: str,
        usuario_id: int,
        token_hash_nuevo: str,
        expires_at_nuevo: dt.datetime,
    ) -> RefreshTokenRegistro | None:
        """Revoca `token_hash_actual` (si seguía vigente) y crea el reemplazo, en una única
        transacción.

        El `UPDATE` que revoca es condicional (`revoked_at IS NULL ... RETURNING id`): si no
        afectó ninguna fila, significa que otro request ya rotó o revocó este mismo token
        (carrera entre dos refresh concurrentes). En ese caso no se crea nada y se devuelve
        `None`; el caller debe tratarlo como un reuso.
        """
        row_factory = class_row(RefreshTokenRegistro)
        async with self._db.connection("MAIN") as conn, conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(_SQL_REVOCAR_SI_VIGENTE, {"token_hash": token_hash_actual})
                fila_revocada = await cur.fetchone()
            if fila_revocada is None:
                return None

            async with conn.cursor(row_factory=row_factory) as cur:
                await cur.execute(
                    _SQL_CREAR,
                    {
                        "usuario_id": usuario_id,
                        "token_hash": token_hash_nuevo,
                        "expires_at": expires_at_nuevo,
                    },
                )
                fila = await cur.fetchone()
        if fila is None:
            raise RuntimeError("El INSERT de ocr_refresh_token no devolvió la fila creada")
        return fila

    async def revocar_por_hash(self, token_hash: str) -> None:
        """Revoca el token si existe y sigue vigente. Idempotente: no falla si no existe."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_REVOCAR_POR_HASH, {"token_hash": token_hash})

    async def revocar_todos_de_usuario(self, usuario_id: int) -> None:
        """Revoca todos los refresh tokens activos del usuario (detección de robo)."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_REVOCAR_TODOS_DE_USUARIO, {"usuario_id": usuario_id})
