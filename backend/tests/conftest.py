"""Fixtures compartidas para los tests del backend.

Las variables de entorno de acá abajo no son secretos: son valores ficticios para que
`Settings()` no falle al importar la app en los tests. Ningún test abre una conexión real
(los repositorios siempre se reemplazan con fakes vía `app.dependency_overrides`).
"""

import os

os.environ.setdefault("OCR_RAG_DB_MAIN_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OCR_RAG_JWT_SIGNING_KEY", "clave-de-test-no-usar-en-produccion")
os.environ.setdefault("OCR_RAG_JWT_ALGORITHM", "HS256")
os.environ.setdefault("OCR_RAG_OPENAI_API_KEY", "sk-test")
os.environ.setdefault("OCR_RAG_CORS_ORIGINS", "http://localhost:5173")

# ruff: noqa: E402 -- las variables de entorno deben fijarse antes de importar la app.

import datetime as dt
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from ocr_rag.api.dependencies import get_auth_service, get_health_service, get_usuario_service
from ocr_rag.api.main import app
from ocr_rag.application.services.auth_service import AuthService
from ocr_rag.application.services.health_service import HealthService
from ocr_rag.application.services.usuario_service import UsuarioService
from ocr_rag.application.validators.auth_validator import AuthValidator
from ocr_rag.application.validators.usuario_validator import UsuarioValidator
from ocr_rag.core.exceptions import UnauthorizedError
from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales
from ocr_rag.core.settings import get_settings


class FakeHealthRepository:
    """Implementación en memoria de `HealthRepository` (`core.repositories`), para tests."""

    def __init__(self, *, conexion_ok: bool = True) -> None:
        self.conexion_ok = conexion_ok

    async def verificar_conexion(self) -> bool:
        return self.conexion_ok


class FakeUsuarioRepository:
    """Implementación en memoria de `UsuarioRepository` (`core.repositories`), para tests."""

    def __init__(
        self,
        usuarios: dict[int, CurrentUserResponse] | None = None,
        credenciales: dict[str, UsuarioCredenciales] | None = None,
    ) -> None:
        self._usuarios = usuarios or {}
        self._credenciales = credenciales or {}
        self._usernames_existentes: set[str] = set(self._credenciales)

    async def obtener_usuario_actual(self, usuario_id: int) -> CurrentUserResponse | None:
        return self._usuarios.get(usuario_id)

    async def obtener_credenciales_activas(self, username: str) -> UsuarioCredenciales | None:
        return self._credenciales.get(username)

    async def existe_username(self, username: str) -> bool:
        return username in self._usernames_existentes

    async def crear(self, username: str, password_hash: str, nombre_completo: str) -> int:
        nuevo_id = max([*self._usuarios.keys(), 0]) + 1
        self._usernames_existentes.add(username)
        return nuevo_id

    async def asignar_rol(self, usuario_id: int, rol_codigo: str) -> None:
        return None


class FakeRefreshTokenRepository:
    """Implementación en memoria de `RefreshTokenRepository` (`core.repositories`), para tests."""

    def __init__(self, registros: dict[str, RefreshTokenRegistro] | None = None) -> None:
        self._registros = registros or {}
        self._siguiente_id = max([r.id for r in self._registros.values()], default=0) + 1

    async def crear(
        self, usuario_id: int, token_hash: str, expires_at: dt.datetime
    ) -> RefreshTokenRegistro:
        registro = RefreshTokenRegistro(
            id=self._siguiente_id,
            usuario_id=usuario_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )
        self._siguiente_id += 1
        self._registros[token_hash] = registro
        return registro

    async def obtener_por_hash(self, token_hash: str) -> RefreshTokenRegistro | None:
        return self._registros.get(token_hash)

    async def rotar(
        self,
        token_hash_actual: str,
        usuario_id: int,
        token_hash_nuevo: str,
        expires_at_nuevo: dt.datetime,
    ) -> RefreshTokenRegistro | None:
        """Revoca `token_hash_actual` solo si seguía vigente; si no, devuelve `None`.

        Simula el `UPDATE ... WHERE revoked_at IS NULL` condicional del repositorio real: si
        el token ya no existe o ya estaba revocado, no crea nada (carrera / reuso).
        """
        registro_actual = self._registros.get(token_hash_actual)
        if registro_actual is None or registro_actual.revoked_at is not None:
            return None
        await self.revocar_por_hash(token_hash_actual)
        return await self.crear(usuario_id, token_hash_nuevo, expires_at_nuevo)

    async def revocar_por_hash(self, token_hash: str) -> None:
        registro = self._registros.get(token_hash)
        if registro is not None and registro.revoked_at is None:
            self._registros[token_hash] = registro.model_copy(
                update={"revoked_at": dt.datetime.now(dt.UTC)}
            )

    async def revocar_todos_de_usuario(self, usuario_id: int) -> None:
        for token_hash, registro in list(self._registros.items()):
            if registro.usuario_id == usuario_id and registro.revoked_at is None:
                self._registros[token_hash] = registro.model_copy(
                    update={"revoked_at": dt.datetime.now(dt.UTC)}
                )

    def agregar(self, registro: RefreshTokenRegistro) -> None:
        """Helper de test: precarga un registro (p. ej. ya vencido o revocado)."""
        self._registros[registro.token_hash] = registro


class FakePasswordHasher:
    """Implementación en memoria de `PasswordHasher` (`core.security`), para tests.

    No usa bcrypt real: compara el password recibido contra el "hash" tal cual (se guarda con
    el prefijo `hash:`), para que los tests sean rápidos y determinísticos.
    """

    @staticmethod
    def hashear_para_test(password: str) -> str:
        return f"hash:{password}"

    async def hashear(self, password: str) -> str:
        return self.hashear_para_test(password)

    async def verificar(self, password: str, password_hash: str) -> bool:
        return password_hash == self.hashear_para_test(password)


class FakeTokenService:
    """Implementación en memoria de `TokenService` (`core.security`), para tests."""

    def crear_access_token(self, usuario_id: int) -> str:
        return f"access-token-de-{usuario_id}"

    def decodificar_access_token(self, token: str) -> int:
        prefijo = "access-token-de-"
        if not token.startswith(prefijo):
            raise UnauthorizedError("El token es inválido o expiró")
        return int(token.removeprefix(prefijo))


@pytest.fixture
def usuario_response() -> CurrentUserResponse:
    """Usuario de prueba con un permiso conocido."""
    return CurrentUserResponse(
        id=1,
        username="ana",
        nombre_completo="Ana Pérez",
        roles=["ADMIN"],
        permisos=["DOCUMENTO_VER"],
    )


# Contraseña "de verdad" del usuario de prueba `ana`, usada por los tests de login.
CONTRASENA_DE_PRUEBA = "clave-correcta-123"


@pytest.fixture
def fake_usuario_repository(usuario_response: CurrentUserResponse) -> FakeUsuarioRepository:
    """Repositorio fake precargado con `usuario_response` y sus credenciales de login."""
    credenciales = UsuarioCredenciales(
        id=usuario_response.id,
        username=usuario_response.username,
        password_hash=FakePasswordHasher.hashear_para_test(CONTRASENA_DE_PRUEBA),
    )
    return FakeUsuarioRepository(
        {usuario_response.id: usuario_response}, {credenciales.username: credenciales}
    )


@pytest.fixture
def fake_refresh_token_repository() -> FakeRefreshTokenRepository:
    """Repositorio fake de refresh tokens, vacío por defecto."""
    return FakeRefreshTokenRepository()


@pytest_asyncio.fixture
async def async_client(
    fake_usuario_repository: FakeUsuarioRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
) -> AsyncIterator[AsyncClient]:
    """Cliente HTTP async contra la app, con los repositorios reemplazados por fakes."""
    app.dependency_overrides[get_health_service] = lambda: HealthService(FakeHealthRepository())
    app.dependency_overrides[get_usuario_service] = lambda: UsuarioService(
        fake_usuario_repository, UsuarioValidator(fake_usuario_repository)
    )
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        fake_refresh_token_repository,
        AuthValidator(fake_usuario_repository, fake_refresh_token_repository, FakePasswordHasher()),
        FakeTokenService(),
        get_settings(),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
