"""Usuario actual y control de permisos a partir del JWT.

Único módulo autorizado a construir un `CurrentUser`. La emisión/verificación del JWT en sí
vive en `TokenService` (`core.security`), compartido con `AuthService`, para no duplicar esa
lógica entre login, refresh y esta dependencia.
"""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from ocr_rag.api.dependencies import get_token_service, get_usuario_service
from ocr_rag.application.services.usuario_service import UsuarioService
from ocr_rag.core.current_user import CurrentUser
from ocr_rag.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from ocr_rag.core.security import TokenService

logger = logging.getLogger(__name__)

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    usuario_service: Annotated[UsuarioService, Depends(get_usuario_service)],
) -> CurrentUser:
    """Valida el access token, resuelve el usuario desde la base y lo devuelve tipado.

    Los claims del token nunca se usan como fuente de roles/permisos: solo identifican al
    usuario (`sub`); sus roles y permisos se leen siempre de la base.
    """
    if token is None:
        raise UnauthorizedError("Falta el token de autenticación")

    usuario_id = token_service.decodificar_access_token(token)

    try:
        usuario = await usuario_service.obtener_usuario_actual(usuario_id)
    except NotFoundError as error:
        # El token es válido pero el usuario ya no existe (o fue desactivado): la sesión
        # queda inválida, no es un 404 de un recurso cualquiera.
        raise UnauthorizedError("El usuario del token ya no existe") from error

    return CurrentUser(
        id=usuario.id,
        username=usuario.username,
        nombre_completo=usuario.nombre_completo,
        roles=usuario.roles,
        permisos=usuario.permisos,
    )


def require_permission(codigo: str) -> Callable[[CurrentUser], CurrentUser]:
    """Dependencia que exige que el usuario actual tenga el permiso `codigo`."""

    def _verificar(
        usuario: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if codigo not in usuario.permisos:
            raise ForbiddenError(f"No tenés el permiso requerido: '{codigo}'")
        return usuario

    return _verificar
