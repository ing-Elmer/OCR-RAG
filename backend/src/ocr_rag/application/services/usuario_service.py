"""Service de datos del usuario autenticado."""

import logging

from ocr_rag.application.validators.usuario_validator import UsuarioValidator
from ocr_rag.core.repositories import UsuarioRepository
from ocr_rag.core.schemas.usuario import CurrentUserResponse

logger = logging.getLogger(__name__)


class UsuarioService:
    """Resuelve los datos del usuario autenticado desde la base."""

    def __init__(self, repositorio: UsuarioRepository, validador: UsuarioValidator) -> None:
        self._repositorio = repositorio
        self._validador = validador

    async def obtener_usuario_actual(self, usuario_id: int) -> CurrentUserResponse:
        """Valida que el usuario exista y devuelve sus datos, roles y permisos."""
        return await self._validador.validar_usuario_existente(usuario_id)
