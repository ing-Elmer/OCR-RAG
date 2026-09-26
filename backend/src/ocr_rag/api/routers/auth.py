"""Router de autenticación: login, refresh y logout."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ocr_rag.api.dependencies import get_auth_service
from ocr_rag.api.responses import ApiResponse
from ocr_rag.application.services.auth_service import AuthService
from ocr_rag.core.schemas.auth import LoginRequest, RefreshRequest, TokenResponse

# Router público: emite las credenciales de sesión, así que no puede exigir un token propio.
# `logout` también es público porque se autentica con el refresh token del body, no con un
# access token (permite cerrar sesión aunque el access token ya haya expirado).
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def iniciar_sesion(
    body: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[TokenResponse]:
    """Verifica username y contraseña, y emite un par de tokens nuevo."""
    tokens = await service.login(body.username, body.password)
    return ApiResponse[TokenResponse].ok("Sesión iniciada", tokens)


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refrescar_sesion(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[TokenResponse]:
    """Rota el refresh token recibido (lo revoca) y emite un par de tokens nuevo."""
    tokens = await service.refrescar(body.refresh_token)
    return ApiResponse[TokenResponse].ok("Sesión renovada", tokens)


@router.post("/logout", response_model=ApiResponse[None])
async def cerrar_sesion(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[None]:
    """Revoca el refresh token recibido. Idempotente: un token desconocido también da 200."""
    await service.cerrar_sesion(body.refresh_token)
    return ApiResponse[None].success("Sesión cerrada")
