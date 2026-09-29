"""Router del usuario autenticado."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ocr_rag.api.dependencies import get_usuario_service
from ocr_rag.api.responses import ApiResponse
from ocr_rag.api.security import get_current_user
from ocr_rag.application.services.usuario_service import UsuarioService
from ocr_rag.core.current_user import CurrentUser
from ocr_rag.core.schemas.usuario import CurrentUserResponse

router = APIRouter(prefix="/api", tags=["usuarios"], dependencies=[Depends(get_current_user)])


@router.get("/me", response_model=ApiResponse[CurrentUserResponse])
async def obtener_usuario_actual(
    usuario_actual: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[UsuarioService, Depends(get_usuario_service)],
) -> ApiResponse[CurrentUserResponse]:
    """Devuelve los datos del usuario autenticado, resueltos desde la base."""
    usuario = await service.obtener_usuario_actual(usuario_actual.id)
    return ApiResponse[CurrentUserResponse].ok("Usuario obtenido", usuario)
