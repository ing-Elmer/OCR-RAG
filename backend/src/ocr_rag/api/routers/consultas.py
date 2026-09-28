"""Router de consultas (RAG) sobre el corpus de documentos procesados."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ocr_rag.api.dependencies import get_consulta_service
from ocr_rag.api.responses import ApiResponse
from ocr_rag.api.security import get_current_user, require_permission
from ocr_rag.application.services.consulta_service import ConsultaService
from ocr_rag.core.current_user import CurrentUser
from ocr_rag.core.schemas.documento import ConsultaRequest, ConsultaResponse

router = APIRouter(
    prefix="/api/consultas", tags=["consultas"], dependencies=[Depends(get_current_user)]
)


@router.post("", response_model=ApiResponse[ConsultaResponse])
async def realizar_consulta(
    body: ConsultaRequest,
    _usuario_actual: Annotated[CurrentUser, Depends(require_permission("CONSULTAS_REALIZAR"))],
    service: Annotated[ConsultaService, Depends(get_consulta_service)],
) -> ApiResponse[ConsultaResponse]:
    """Responde `body.pregunta` con la información más relevante del corpus indexado."""
    resultado = await service.consultar(
        body.pregunta, body.documento_ids, body.top_k, body.tipos_documento
    )
    return ApiResponse[ConsultaResponse].ok("Consulta respondida", resultado)
