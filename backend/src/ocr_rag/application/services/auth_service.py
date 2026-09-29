"""Service de autenticación: login, refresh (con rotación) y logout."""

import datetime as dt
import logging

from ocr_rag.application.validators.auth_validator import (
    MENSAJE_REFRESH_INVALIDO,
    AuthValidator,
)
from ocr_rag.core.exceptions import RefreshTokenReusadoError, UnauthorizedError
from ocr_rag.core.refresh_tokens import generar_refresh_token, hashear_refresh_token
from ocr_rag.core.repositories import RefreshTokenRepository
from ocr_rag.core.schemas.auth import TokenResponse
from ocr_rag.core.security import TokenService
from ocr_rag.core.settings import Settings

logger = logging.getLogger(__name__)


class AuthService:
    """Emite, rota y revoca los tokens de sesión (access JWT + refresh opaco)."""

    def __init__(
        self,
        refresh_token_repositorio: RefreshTokenRepository,
        validador: AuthValidator,
        token_service: TokenService,
        settings: Settings,
    ) -> None:
        self._refresh_token_repositorio = refresh_token_repositorio
        self._validador = validador
        self._token_service = token_service
        self._settings = settings

    async def login(self, username: str, password: str) -> TokenResponse:
        """Verifica las credenciales y emite un par de tokens nuevo."""
        credenciales = await self._validador.validar_login(username, password)
        refresh_token = generar_refresh_token()
        await self._refresh_token_repositorio.crear(
            usuario_id=credenciales.id,
            token_hash=hashear_refresh_token(refresh_token),
            expires_at=self._calcular_expiracion_refresh(),
        )
        return self._armar_respuesta(credenciales.id, refresh_token)

    async def refrescar(self, refresh_token: str) -> TokenResponse:
        """Valida el refresh token, lo rota (revoca el usado) y emite un par nuevo.

        Es el único lugar que revoca *toda* la sesión de un usuario ante un reuso, ya sea
        detectado por el validador (token ya revocado) o por una carrera al rotar (dos
        refresh concurrentes con el mismo token): en ambos casos, mismo mensaje y 401.
        """
        try:
            registro = await self._validador.validar_refresh(refresh_token)
        except RefreshTokenReusadoError as error:
            await self._refresh_token_repositorio.revocar_todos_de_usuario(error.usuario_id)
            raise UnauthorizedError(MENSAJE_REFRESH_INVALIDO) from error

        refresh_token_nuevo = generar_refresh_token()
        registro_nuevo = await self._refresh_token_repositorio.rotar(
            token_hash_actual=registro.token_hash,
            usuario_id=registro.usuario_id,
            token_hash_nuevo=hashear_refresh_token(refresh_token_nuevo),
            expires_at_nuevo=self._calcular_expiracion_refresh(),
        )
        if registro_nuevo is None:
            # Carrera: entre `validar_refresh` y `rotar`, otro request ya consumió este mismo
            # token. Se trata igual que un reuso detectado: se revoca toda la sesión.
            await self._refresh_token_repositorio.revocar_todos_de_usuario(registro.usuario_id)
            raise UnauthorizedError(MENSAJE_REFRESH_INVALIDO)

        return self._armar_respuesta(registro.usuario_id, refresh_token_nuevo)

    async def cerrar_sesion(self, refresh_token: str) -> None:
        """Revoca el refresh token indicado. Idempotente: nunca falla si ya no está vigente."""
        await self._refresh_token_repositorio.revocar_por_hash(hashear_refresh_token(refresh_token))

    def _armar_respuesta(self, usuario_id: int, refresh_token: str) -> TokenResponse:
        """Firma el access token del usuario y arma el par de tokens de respuesta."""
        access_token = self._token_service.crear_access_token(usuario_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.jwt_access_ttl_minutes * 60,
        )

    def _calcular_expiracion_refresh(self) -> dt.datetime:
        """Fecha de expiración de un refresh token recién emitido."""
        return dt.datetime.now(dt.UTC) + dt.timedelta(days=self._settings.refresh_ttl_days)
