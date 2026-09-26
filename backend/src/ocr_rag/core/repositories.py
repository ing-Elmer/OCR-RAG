"""Interfaces (`Protocol`) de los repositorios: las implementa `infrastructure`."""

from datetime import datetime
from typing import Protocol

from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales


class HealthRepository(Protocol):
    """Verifica el estado de la conexión principal a la base de datos."""

    async def verificar_conexion(self) -> bool:
        """Ejecuta un `SELECT 1` contra la conexión principal y devuelve si respondió."""
        ...


class UsuarioRepository(Protocol):
    """Acceso a los datos de usuarios, roles y permisos."""

    async def obtener_usuario_actual(self, usuario_id: int) -> CurrentUserResponse | None:
        """Devuelve el usuario activo con sus roles y permisos, o `None` si no existe."""
        ...

    async def obtener_credenciales_activas(self, username: str) -> UsuarioCredenciales | None:
        """Devuelve `id`, `username` y `password_hash` si el usuario existe y está activo."""
        ...

    async def existe_username(self, username: str) -> bool:
        """Indica si ya existe un usuario (activo o no) con ese `username`."""
        ...

    async def crear(self, username: str, password_hash: str, nombre_completo: str) -> int:
        """Crea un usuario activo y devuelve su id."""
        ...

    async def asignar_rol(self, usuario_id: int, rol_codigo: str) -> None:
        """Asigna el rol `rol_codigo` al usuario. Lanza `NotFoundError` si el rol no existe."""
        ...


class RefreshTokenRepository(Protocol):
    """Acceso a los refresh tokens emitidos: rotativos, opacos, guardados hasheados."""

    async def crear(
        self, usuario_id: int, token_hash: str, expires_at: datetime
    ) -> RefreshTokenRegistro:
        """Crea un refresh token nuevo para el usuario y lo devuelve."""
        ...

    async def obtener_por_hash(self, token_hash: str) -> RefreshTokenRegistro | None:
        """Busca un refresh token por su hash, esté vigente o revocado."""
        ...

    async def rotar(
        self,
        token_hash_actual: str,
        usuario_id: int,
        token_hash_nuevo: str,
        expires_at_nuevo: datetime,
    ) -> RefreshTokenRegistro | None:
        """Revoca `token_hash_actual` (si seguía vigente) y crea el reemplazo, en una única
        transacción.

        Devuelve `None` sin crear nada si `token_hash_actual` ya no estaba vigente al momento
        de revocarlo (carrera: otro request lo rotó o lo revocó primero). El caller debe tratar
        ese caso como un reuso de refresh token.
        """
        ...

    async def revocar_por_hash(self, token_hash: str) -> None:
        """Revoca el token si existe y sigue vigente. Idempotente: no falla si no existe."""
        ...

    async def revocar_todos_de_usuario(self, usuario_id: int) -> None:
        """Revoca todos los refresh tokens activos del usuario (detección de robo)."""
        ...
