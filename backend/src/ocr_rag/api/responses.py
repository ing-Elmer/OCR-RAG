"""Envelope estándar de respuestas de la API (`ApiResponse`), compartido con el frontend."""

from enum import StrEnum

from pydantic import BaseModel


class ApiStatus(StrEnum):
    """Valores posibles del campo `status` del envelope."""

    SUCCESS = "Success"
    CREATED = "Created"
    ERROR = "Error"


class ApiResponse[T](BaseModel):
    """Envelope estándar de toda respuesta HTTP: `status`, `message`, `data`, `errors`, `meta`."""

    status: ApiStatus
    message: str
    data: T | None = None
    errors: dict[str, list[str]] | None = None
    meta: dict[str, object] | None = None

    @classmethod
    def ok(cls, message: str, data: T) -> "ApiResponse[T]":
        """Respuesta exitosa (200) con datos."""
        return ApiResponse[T](status=ApiStatus.SUCCESS, message=message, data=data)

    @classmethod
    def success(cls, message: str) -> "ApiResponse[None]":
        """Respuesta exitosa (200) sin datos."""
        return ApiResponse[None](status=ApiStatus.SUCCESS, message=message, data=None)

    @classmethod
    def created(cls, message: str, data: T) -> "ApiResponse[T]":
        """Respuesta de creación (201) con el recurso creado."""
        return ApiResponse[T](status=ApiStatus.CREATED, message=message, data=data)

    @classmethod
    def bad_request(cls, message: str, errors: dict[str, list[str]]) -> "ApiResponse[None]":
        """Respuesta de error (400) con errores por campo."""
        return ApiResponse[None](status=ApiStatus.ERROR, message=message, errors=errors, data=None)

    @classmethod
    def internal_error(cls, message: str) -> "ApiResponse[None]":
        """Respuesta de error (500) genérica, sin detalle interno."""
        return ApiResponse[None](status=ApiStatus.ERROR, message=message, data=None)
