"""DTOs de autenticación: login, refresh y el par de tokens emitido."""

from datetime import datetime

from pydantic import Field

from ocr_rag.core.schemas.base import CamelModel


class LoginRequest(CamelModel):
    """Credenciales para `POST /api/auth/login`."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class RefreshRequest(CamelModel):
    """Body de `POST /api/auth/refresh` y de `POST /api/auth/logout`."""

    refresh_token: str = Field(min_length=1)


class TokenResponse(CamelModel):
    """Par de tokens emitido por login y por refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRegistro(CamelModel):
    """Refresh token tal como está persistido. Uso interno: nunca se expone por la API."""

    id: int
    usuario_id: int
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
