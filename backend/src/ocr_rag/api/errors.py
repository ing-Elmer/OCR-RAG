"""Exception handlers: único lugar que traduce excepciones al envelope `ApiResponse`."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ocr_rag.api.responses import ApiResponse, ApiStatus
from ocr_rag.core.exceptions import DomainError
from ocr_rag.core.exceptions import ValidationError as CoreValidationError

logger = logging.getLogger(__name__)

# Segmentos de `loc` que no son parte del nombre del campo para el usuario final.
_SEGMENTOS_IGNORADOS = {"body", "query", "path"}


def _errores_desde_validacion(exc: RequestValidationError) -> dict[str, list[str]]:
    """Arma `{ campo: [mensajes] }` a partir de los errores de validación de FastAPI."""
    errores: dict[str, list[str]] = {}
    for error in exc.errors():
        segmentos = [str(parte) for parte in error["loc"] if parte not in _SEGMENTOS_IGNORADOS]
        campo = segmentos[-1] if segmentos else "general"
        errores.setdefault(campo, []).append(error["msg"])
    return errores


def _responder(status_code: int, cuerpo: ApiResponse[None]) -> JSONResponse:
    """Serializa el envelope por alias (camelCase) con el status HTTP indicado."""
    return JSONResponse(status_code=status_code, content=jsonable_encoder(cuerpo, by_alias=True))


def registrar_manejadores_de_error(app: FastAPI) -> None:
    """Registra en `app` todos los exception handlers del estándar."""

    @app.exception_handler(RequestValidationError)
    async def _manejar_validacion_de_request(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Body o query inválidos: 400 con el envelope, nunca el 422 por defecto."""
        cuerpo = ApiResponse[None].bad_request(
            "Los datos enviados no son válidos", _errores_desde_validacion(exc)
        )
        return _responder(status.HTTP_400_BAD_REQUEST, cuerpo)

    @app.exception_handler(CoreValidationError)
    async def _manejar_validacion_de_negocio(
        request: Request, exc: CoreValidationError
    ) -> JSONResponse:
        """Regla de negocio incumplida (validador de `application`): 400."""
        cuerpo = ApiResponse[None].bad_request(exc.message, exc.errors or {})
        return _responder(status.HTTP_400_BAD_REQUEST, cuerpo)

    @app.exception_handler(DomainError)
    async def _manejar_error_de_dominio(request: Request, exc: DomainError) -> JSONResponse:
        """Cualquier otra excepción de dominio: usa el `status_code` que declara la clase."""
        cuerpo = ApiResponse[None](status=ApiStatus.ERROR, message=exc.message, errors=exc.errors)
        return _responder(exc.status_code, cuerpo)

    @app.exception_handler(Exception)
    async def _manejar_error_no_controlado(request: Request, exc: Exception) -> JSONResponse:
        """Cualquier excepción no prevista: 500 genérico; el detalle solo va al log."""
        logger.exception("Error no controlado en %s %s", request.method, request.url.path)
        cuerpo = ApiResponse[None].internal_error("Ocurrió un error inesperado")
        return _responder(status.HTTP_500_INTERNAL_SERVER_ERROR, cuerpo)
