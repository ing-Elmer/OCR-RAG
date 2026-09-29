"""Validaciones de negocio sobre usuarios."""

from ocr_rag.core.exceptions import NotFoundError
from ocr_rag.core.repositories import UsuarioRepository
from ocr_rag.core.schemas.usuario import CurrentUserResponse


class UsuarioValidator:
    """Valida que el usuario exista y esté activo antes de que el service lo use."""

    def __init__(self, repositorio: UsuarioRepository) -> None:
        self._repositorio = repositorio

    async def validar_usuario_existente(self, usuario_id: int) -> CurrentUserResponse:
        """Verifica que el usuario exista y esté activo; devuelve sus datos.

        Lanza `NotFoundError` si no hay un usuario activo con ese id.
        """
        usuario = await self._repositorio.obtener_usuario_actual(usuario_id)
        if usuario is None:
            raise NotFoundError(f"No se encontró el usuario {usuario_id}")
        return usuario
