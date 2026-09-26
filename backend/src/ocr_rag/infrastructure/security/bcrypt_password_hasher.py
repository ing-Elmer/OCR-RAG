"""Hashing de contraseñas con bcrypt."""

import bcrypt
from fastapi.concurrency import run_in_threadpool

# Costo por defecto (producción): seguridad-config exige un mínimo de 12.
_COSTO_BCRYPT_PRODUCCION = 12


class BcryptPasswordHasher:
    """Implementación de `PasswordHasher` (`core.security`) sobre bcrypt.

    bcrypt es bloqueante por diseño (cómputo intensivo): las operaciones reales corren en un
    threadpool para no bloquear el loop de eventos, igual que `TesseractOcrClient`.
    """

    def __init__(self, costo: int = _COSTO_BCRYPT_PRODUCCION) -> None:
        """Un `costo` bajo (< 12) solo está permitido en tests, para que corran rápido."""
        self._costo = costo

    async def hashear(self, password: str) -> str:
        """Devuelve el hash bcrypt de `password`."""
        return await run_in_threadpool(self._hashear_sync, password)

    async def verificar(self, password: str, password_hash: str) -> bool:
        """Compara `password` contra `password_hash`; nunca lanza si no coinciden."""
        return await run_in_threadpool(self._verificar_sync, password, password_hash)

    def _hashear_sync(self, password: str) -> str:
        """Ejecuta el hashing. Nunca se llama directamente desde código async."""
        sal = bcrypt.gensalt(rounds=self._costo)
        return bcrypt.hashpw(password.encode("utf-8"), sal).decode("utf-8")

    @staticmethod
    def _verificar_sync(password: str, password_hash: str) -> bool:
        """Ejecuta la verificación. Nunca se llama directamente desde código async."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            # `password_hash` no tiene formato bcrypt válido: se trata como no coincidente.
            return False
