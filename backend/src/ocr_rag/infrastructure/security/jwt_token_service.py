"""Emisión y validación de access tokens (JWT) sobre PyJWT."""

import datetime as dt

import jwt

from ocr_rag.core.exceptions import UnauthorizedError
from ocr_rag.core.settings import Settings

_TIPO_ACCESS = "access"


class JwtTokenService:
    """Implementación de `TokenService` (`core.security`) usando PyJWT."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def crear_access_token(self, usuario_id: int) -> str:
        """Firma un access token para `usuario_id`, con el TTL configurado en `Settings`."""
        ahora = dt.datetime.now(dt.UTC)
        claims = {
            "sub": str(usuario_id),
            "type": _TIPO_ACCESS,
            "iat": ahora,
            "exp": ahora + dt.timedelta(minutes=self._settings.jwt_access_ttl_minutes),
        }
        return jwt.encode(
            claims,
            self._settings.jwt_signing_key.get_secret_value(),
            algorithm=self._settings.jwt_algorithm,
        )

    def decodificar_access_token(self, token: str) -> int:
        """Valida el access token y devuelve el id de usuario (`sub`).

        Lanza `UnauthorizedError` si el token es inválido, expiró o no es de tipo "access".
        """
        try:
            claims = jwt.decode(
                token,
                self._settings.jwt_signing_key.get_secret_value(),
                algorithms=[self._settings.jwt_algorithm],
            )
        except jwt.PyJWTError as error:
            raise UnauthorizedError("El token es inválido o expiró") from error

        if claims.get("type") != _TIPO_ACCESS:
            raise UnauthorizedError("El token no es un access token")

        usuario_id_raw = claims.get("sub")
        if usuario_id_raw is None:
            raise UnauthorizedError("El token no incluye el usuario")

        try:
            return int(usuario_id_raw)
        except (TypeError, ValueError) as error:
            raise UnauthorizedError("El token no incluye un usuario válido") from error
