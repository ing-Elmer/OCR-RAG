"""Validaciones de negocio para crear el usuario administrador desde el CLI."""

from ocr_rag.core.exceptions import ValidationError
from ocr_rag.core.repositories import UsuarioRepository

_LONGITUD_MINIMA_PASSWORD = 12


class CrearAdminValidator:
    """Valida los datos para crear un usuario administrador antes de persistirlo."""

    def __init__(self, repositorio: UsuarioRepository) -> None:
        self._repositorio = repositorio

    async def validar(self, username: str, password: str) -> None:
        """Verifica que el `username` no exista y que la contraseña cumpla el largo mínimo."""
        errores: dict[str, list[str]] = {}

        if len(password) < _LONGITUD_MINIMA_PASSWORD:
            errores.setdefault("password", []).append(
                f"La contraseña debe tener al menos {_LONGITUD_MINIMA_PASSWORD} caracteres"
            )

        if await self._repositorio.existe_username(username):
            errores.setdefault("username", []).append(
                f"Ya existe un usuario con el username '{username}'"
            )

        if errores:
            raise ValidationError("Los datos ingresados no son válidos", errores)
