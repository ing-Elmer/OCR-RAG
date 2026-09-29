"""Interfaces (`Protocol`) de los componentes de seguridad: implementados en `infrastructure`.

Evitan duplicar la emisión/verificación de JWT y el hashing de contraseñas entre `api/security.py`
y los distintos flujos de `AuthService` (login, refresh).
"""

from typing import Protocol


class PasswordHasher(Protocol):
    """Hashea y verifica contraseñas con bcrypt.

    bcrypt es bloqueante: la implementación corre el cómputo real en un threadpool.
    """

    async def hashear(self, password: str) -> str:
        """Devuelve el hash de `password`."""
        ...

    async def verificar(self, password: str, password_hash: str) -> bool:
        """Compara `password` contra `password_hash`. Nunca lanza si no coinciden."""
        ...


class TokenService(Protocol):
    """Emite y valida los access tokens (JWT) de la aplicación."""

    def crear_access_token(self, usuario_id: int) -> str:
        """Firma un access token para `usuario_id`, con el TTL configurado."""
        ...

    def decodificar_access_token(self, token: str) -> int:
        """Valida el access token y devuelve el id de usuario (`sub`).

        Lanza `UnauthorizedError` (de `core.exceptions`) si el token es inválido, expiró o no
        es de tipo "access".
        """
        ...
