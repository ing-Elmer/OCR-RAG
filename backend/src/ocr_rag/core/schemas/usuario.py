"""DTOs de usuarios."""

from ocr_rag.core.schemas.base import CamelModel


class CurrentUserResponse(CamelModel):
    """Datos del usuario autenticado, resueltos desde la base (no desde el JWT)."""

    id: int
    username: str
    nombre_completo: str
    roles: list[str]
    permisos: list[str]


class UsuarioCredenciales(CamelModel):
    """Credenciales de un usuario activo, usadas solo para verificar el login."""

    id: int
    username: str
    password_hash: str
