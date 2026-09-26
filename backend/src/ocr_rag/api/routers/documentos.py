"""Router de documentos: carga, listado y detalle."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ocr_rag.api.dependencies import get_documento_service
from ocr_rag.api.forms.documento_forms import DocumentoCargaForm
from ocr_rag.api.responses import ApiResponse, ApiStatus
from ocr_rag.api.security import get_current_user, require_permission
from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.core.current_user import CurrentUser
from ocr_rag.core.schemas.documento import DocumentoResponse

router = APIRouter(
    prefix="/api/documentos", tags=["documentos"], dependencies=[Depends(get_current_user)]
)

_LIMITE_POR_DEFECTO = 20
_LIMITE_MAXIMO = 100


@router.post(
    "",
    response_model=ApiResponse[DocumentoResponse],
    status_code=status.HTTP_201_CREATED,
)
async def cargar_documento(
    form: Annotated[DocumentoCargaForm, Depends()],
    usuario_actual: Annotated[CurrentUser, Depends(require_permission("DOCUMENTOS_CARGAR"))],
    service: Annotated[DocumentoService, Depends(get_documento_service)],
) -> ApiResponse[DocumentoResponse]:
    """Sube un documento, lo guarda como `pendiente` y encola su procesamiento OCR + embeddings."""
    contenido = await form.archivo.read()
    documento = await service.cargar(
        nombre_archivo=form.archivo.filename or "",
        tipo_contenido=form.archivo.content_type or "",
        contenido=contenido,
        idioma=form.idioma,
        creado_por_id=usuario_actual.id,
    )
    return ApiResponse[DocumentoResponse].created("Documento cargado", documento)


@router.get("", response_model=ApiResponse[list[DocumentoResponse]])
async def listar_documentos(
    _usuario_actual: Annotated[CurrentUser, Depends(require_permission("DOCUMENTOS_VER"))],
    service: Annotated[DocumentoService, Depends(get_documento_service)],
    limite: Annotated[int, Query(ge=1, le=_LIMITE_MAXIMO)] = _LIMITE_POR_DEFECTO,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiResponse[list[DocumentoResponse]]:
    """Lista los documentos cargados, paginados y ordenados por fecha de carga descendente."""
    documentos, total = await service.listar(limite, offset)
    return ApiResponse[list[DocumentoResponse]](
        status=ApiStatus.SUCCESS,
        message="Documentos obtenidos",
        data=documentos,
        meta={"total": total, "limite": limite, "offset": offset},
    )


@router.get("/{documento_id}", response_model=ApiResponse[DocumentoResponse])
async def obtener_documento(
    documento_id: int,
    _usuario_actual: Annotated[CurrentUser, Depends(require_permission("DOCUMENTOS_VER"))],
    service: Annotated[DocumentoService, Depends(get_documento_service)],
) -> ApiResponse[DocumentoResponse]:
    """Devuelve el detalle de un documento. Responde 404 si no existe."""
    documento = await service.obtener(documento_id)
    return ApiResponse[DocumentoResponse].ok("Documento obtenido", documento)
