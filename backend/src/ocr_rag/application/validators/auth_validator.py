"""Validaciones de negocio de autenticación: credenciales de login y vigencia del refresh."""

import datetime as dt

from ocr_rag.core.exceptions import RefreshTokenReusadoError, UnauthorizedError
from ocr_rag.core.refresh_tokens import hashear_refresh_token
from ocr_rag.core.repositories import RefreshTokenRepository, UsuarioRepository
from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.core.schemas.usuario import UsuarioCredenciales
from ocr_rag.core.security import PasswordHasher

_MENSAJE_CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos"

# Público: lo reutiliza `AuthService` para que el mensaje sea idéntico en todos los casos de
# refresh inválido (inexistente, vencido, reusado o "carrera" detectada al rotar).
MENSAJE_REFRESH_INVALIDO = "El refresh token es inválido o expiró"

# Hash bcrypt (costo 12) de una contraseña que nadie usa. Sirve solo para que verificar un
# login con un username inexistente tarde lo mismo que uno real, y así no delatar por timing
# si el username existe o no.
_HASH_DUMMY = "$2b$12$kgtu.A6ChbQ3XLqhABfCGOcRyPPCCE/4xPQ8EOBKDrFUooVYvYbDy"


class AuthValidator:
    """Valida credenciales de login y la vigencia de un refresh token."""

    def __init__(
        self,
        usuario_repositorio: UsuarioRepository,
        refresh_token_repositorio: RefreshTokenRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._usuario_repositorio = usuario_repositorio
        self._refresh_token_repositorio = refresh_token_repositorio
        self._password_hasher = password_hasher

    async def validar_login(self, username: str, password: str) -> UsuarioCredenciales:
        """Verifica usuario y contraseña.

        Usuario inexistente, contraseña incorrecta y usuario inactivo lanzan el mismo error,
        con el mismo mensaje, para no revelar cuál de los tres ocurrió.
        """
        credenciales = await self._usuario_repositorio.obtener_credenciales_activas(username)
        if credenciales is None:
            # Igualamos el tiempo de respuesta al de un login válido verificando contra un
            # hash dummy, aunque el resultado se descarte.
            await self._password_hasher.verificar(password, _HASH_DUMMY)
            raise UnauthorizedError(_MENSAJE_CREDENCIALES_INVALIDAS)

        if not await self._password_hasher.verificar(password, credenciales.password_hash):
            raise UnauthorizedError(_MENSAJE_CREDENCIALES_INVALIDAS)

        return credenciales

    async def validar_refresh(self, refresh_token: str) -> RefreshTokenRegistro:
        """Verifica que el refresh token exista, esté vigente y su usuario siga activo.

        El validador solo detecta y lanza; nunca escribe en la base. Si el token ya estaba
        revocado (reuso, posible robo), lanza `RefreshTokenReusadoError` en lugar del genérico
        `UnauthorizedError`, para que `AuthService` sea el único lugar que decide revocar toda
        la sesión del usuario.
        """
        token_hash = hashear_refresh_token(refresh_token)
        registro = await self._refresh_token_repositorio.obtener_por_hash(token_hash)
        if registro is None:
            raise UnauthorizedError(MENSAJE_REFRESH_INVALIDO)

        if registro.revoked_at is not None:
            raise RefreshTokenReusadoError(MENSAJE_REFRESH_INVALIDO, registro.usuario_id)

        if registro.expires_at <= dt.datetime.now(dt.UTC):
            raise UnauthorizedError(MENSAJE_REFRESH_INVALIDO)

        usuario_activo = await self._usuario_repositorio.obtener_usuario_actual(registro.usuario_id)
        if usuario_activo is None:
            raise UnauthorizedError(MENSAJE_REFRESH_INVALIDO)

        return registro
