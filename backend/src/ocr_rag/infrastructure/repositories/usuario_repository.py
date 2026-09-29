"""Repositorio de usuarios: datos, roles y permisos desde PostgreSQL."""

from psycopg.rows import class_row

from ocr_rag.core.exceptions import NotFoundError
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales
from ocr_rag.infrastructure.db import ConnectionFactory

_SQL_OBTENER_USUARIO_ACTUAL = """
    SELECT u.id,
           u.username,
           u.nombre_completo,
           COALESCE(
               array_agg(DISTINCT r.codigo) FILTER (WHERE r.codigo IS NOT NULL),
               ARRAY[]::text[]
           ) AS roles,
           COALESCE(
               array_agg(DISTINCT p.codigo) FILTER (WHERE p.codigo IS NOT NULL),
               ARRAY[]::text[]
           ) AS permisos
      FROM ocr_rag.ocr_usuario u
      LEFT JOIN ocr_rag.ocr_usuario_rol ur ON ur.usuario_id = u.id
      LEFT JOIN ocr_rag.ocr_rol r ON r.id = ur.rol_id
      LEFT JOIN ocr_rag.ocr_rol_permiso rp ON rp.rol_id = r.id
      LEFT JOIN ocr_rag.ocr_permiso p ON p.id = rp.permiso_id
     WHERE u.id = %(usuario_id)s
       AND u.activo = true
     GROUP BY u.id, u.username, u.nombre_completo
"""

_SQL_OBTENER_CREDENCIALES_ACTIVAS = """
    SELECT id, username, password_hash
      FROM ocr_rag.ocr_usuario
     WHERE username = %(username)s
       AND activo = true
"""

_SQL_EXISTE_USERNAME = """
    SELECT 1
      FROM ocr_rag.ocr_usuario
     WHERE username = %(username)s
"""

_SQL_CREAR_USUARIO = """
    INSERT INTO ocr_rag.ocr_usuario (username, password_hash, nombre_completo)
    VALUES (%(username)s, %(password_hash)s, %(nombre_completo)s)
    RETURNING id
"""

_SQL_OBTENER_ROL_ID = """
    SELECT id
      FROM ocr_rag.ocr_rol
     WHERE codigo = %(codigo)s
"""

_SQL_ASIGNAR_ROL = """
    INSERT INTO ocr_rag.ocr_usuario_rol (usuario_id, rol_id)
    VALUES (%(usuario_id)s, %(rol_id)s)
    ON CONFLICT (usuario_id, rol_id) DO NOTHING
"""


class PostgresUsuarioRepository:
    """Implementación de `UsuarioRepository` (`core.repositories`) sobre PostgreSQL."""

    def __init__(self, db: ConnectionFactory) -> None:
        self._db = db

    async def obtener_usuario_actual(self, usuario_id: int) -> CurrentUserResponse | None:
        """Devuelve el usuario activo con sus roles y permisos, o `None` si no existe."""
        row_factory = class_row(CurrentUserResponse)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(_SQL_OBTENER_USUARIO_ACTUAL, {"usuario_id": usuario_id})
            return await cur.fetchone()

    async def obtener_credenciales_activas(self, username: str) -> UsuarioCredenciales | None:
        """Devuelve `id`, `username` y `password_hash` si el usuario existe y está activo."""
        row_factory = class_row(UsuarioCredenciales)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(_SQL_OBTENER_CREDENCIALES_ACTIVAS, {"username": username})
            return await cur.fetchone()

    async def existe_username(self, username: str) -> bool:
        """Indica si ya existe un usuario (activo o no) con ese `username`."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_EXISTE_USERNAME, {"username": username})
            fila = await cur.fetchone()
            return fila is not None

    async def crear(self, username: str, password_hash: str, nombre_completo: str) -> int:
        """Crea un usuario activo y devuelve su id."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(
                _SQL_CREAR_USUARIO,
                {
                    "username": username,
                    "password_hash": password_hash,
                    "nombre_completo": nombre_completo,
                },
            )
            fila = await cur.fetchone()
            if fila is None:
                raise RuntimeError("El INSERT de ocr_usuario no devolvió el id creado")
            usuario_id: int = fila[0]
            return usuario_id

    async def asignar_rol(self, usuario_id: int, rol_codigo: str) -> None:
        """Asigna el rol `rol_codigo` al usuario. Lanza `NotFoundError` si el rol no existe."""
        async with self._db.connection("MAIN") as conn:
            async with conn.cursor() as cur:
                await cur.execute(_SQL_OBTENER_ROL_ID, {"codigo": rol_codigo})
                fila_rol = await cur.fetchone()
            if fila_rol is None:
                raise NotFoundError(f"No existe el rol '{rol_codigo}'")
            rol_id: int = fila_rol[0]
            async with conn.cursor() as cur:
                await cur.execute(_SQL_ASIGNAR_ROL, {"usuario_id": usuario_id, "rol_id": rol_id})
