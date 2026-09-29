"""Generación y hashing de refresh tokens opacos.

El valor real del refresh token nunca se persiste: solo su hash SHA-256 (ver
`RefreshTokenRepository` en `core/repositories.py`), para que una fuga de la base no permita
reconstruir tokens válidos. Funciones puras compartidas por `AuthService` (al emitir/rotar) y
`AuthValidator` (al buscar el token recibido).
"""

import hashlib
import secrets

_LONGITUD_TOKEN_BYTES = 48


def generar_refresh_token() -> str:
    """Genera un refresh token opaco, aleatorio y no adivinable."""
    return secrets.token_urlsafe(_LONGITUD_TOKEN_BYTES)


def hashear_refresh_token(token: str) -> str:
    """Calcula el hash SHA-256 (hex) de un refresh token, para guardarlo o buscarlo."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
