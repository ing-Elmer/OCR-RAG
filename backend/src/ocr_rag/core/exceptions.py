"""Excepciones de dominio.

Cada excepción declara su propio `status_code` HTTP como atributo de clase; el único lugar
que las traduce a una respuesta es `api/errors.py`.
"""


class DomainError(Exception):
    """Excepción base de dominio. Las subclases fijan `status_code`."""

    status_code: int = 500

    def __init__(self, message: str, errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors


class ValidationError(DomainError):
    """Los datos no cumplen una regla de negocio (no confundir con el 422 de FastAPI)."""

    status_code = 400


class UnauthorizedError(DomainError):
    """Falta autenticación o el token no es válido."""

    status_code = 401


class RefreshTokenReusadoError(UnauthorizedError):
    """Se intentó usar un refresh token que ya había sido revocado (posible robo).

    La lanza `AuthValidator` (que solo detecta, nunca escribe); `AuthService` la captura para
    revocar todas las sesiones activas de `usuario_id` antes de responder 401.
    """

    def __init__(self, message: str, usuario_id: int) -> None:
        super().__init__(message)
        self.usuario_id = usuario_id


class ForbiddenError(DomainError):
    """El usuario autenticado no tiene el permiso requerido."""

    status_code = 403


class NotFoundError(DomainError):
    """El recurso solicitado no existe."""

    status_code = 404


class ConflictError(DomainError):
    """La operación entra en conflicto con el estado actual del recurso."""

    status_code = 409
