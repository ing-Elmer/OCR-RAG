"""Tests del `AuthService`."""

import datetime as dt

import pytest

from ocr_rag.application.services.auth_service import AuthService
from ocr_rag.application.validators.auth_validator import AuthValidator
from ocr_rag.core.exceptions import UnauthorizedError
from ocr_rag.core.refresh_tokens import hashear_refresh_token
from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales
from ocr_rag.core.settings import get_settings
from tests.conftest import (
    CONTRASENA_DE_PRUEBA,
    FakePasswordHasher,
    FakeRefreshTokenRepository,
    FakeTokenService,
    FakeUsuarioRepository,
)


def _crear_service(
    usuario_repositorio: FakeUsuarioRepository,
    refresh_token_repositorio: FakeRefreshTokenRepository,
) -> AuthService:
    validador = AuthValidator(usuario_repositorio, refresh_token_repositorio, FakePasswordHasher())
    return AuthService(refresh_token_repositorio, validador, FakeTokenService(), get_settings())


async def test_login_credenciales_correctas_devuelve_un_par_de_tokens() -> None:
    credenciales = UsuarioCredenciales(
        id=1,
        username="ana",
        password_hash=FakePasswordHasher.hashear_para_test(CONTRASENA_DE_PRUEBA),
    )
    usuario_repositorio = FakeUsuarioRepository(credenciales={"ana": credenciales})
    refresh_token_repositorio = FakeRefreshTokenRepository()
    service = _crear_service(usuario_repositorio, refresh_token_repositorio)

    tokens = await service.login("ana", CONTRASENA_DE_PRUEBA)

    assert tokens.access_token == "access-token-de-1"
    assert tokens.token_type == "bearer"
    assert tokens.expires_in == get_settings().jwt_access_ttl_minutes * 60
    registro = await refresh_token_repositorio.obtener_por_hash(
        hashear_refresh_token(tokens.refresh_token)
    )
    assert registro is not None
    assert registro.usuario_id == 1
    assert registro.revoked_at is None


async def test_login_credenciales_incorrectas_lanza_unauthorized() -> None:
    service = _crear_service(FakeUsuarioRepository(), FakeRefreshTokenRepository())

    with pytest.raises(UnauthorizedError):
        await service.login("no-existe", "cualquier-password")


async def test_refrescar_token_vigente_rota_y_revoca_el_anterior() -> None:
    usuario = CurrentUserResponse(
        id=1, username="ana", nombre_completo="Ana Pérez", roles=[], permisos=[]
    )
    usuario_repositorio = FakeUsuarioRepository({1: usuario})
    refresh_token_repositorio = FakeRefreshTokenRepository()
    token_viejo = "refresh-viejo"
    refresh_token_repositorio.agregar(
        RefreshTokenRegistro(
            id=1,
            usuario_id=1,
            token_hash=hashear_refresh_token(token_viejo),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            revoked_at=None,
        )
    )
    service = _crear_service(usuario_repositorio, refresh_token_repositorio)

    tokens = await service.refrescar(token_viejo)

    assert tokens.access_token == "access-token-de-1"
    assert tokens.refresh_token != token_viejo

    registro_viejo = await refresh_token_repositorio.obtener_por_hash(
        hashear_refresh_token(token_viejo)
    )
    assert registro_viejo is not None
    assert registro_viejo.revoked_at is not None

    registro_nuevo = await refresh_token_repositorio.obtener_por_hash(
        hashear_refresh_token(tokens.refresh_token)
    )
    assert registro_nuevo is not None
    assert registro_nuevo.revoked_at is None


async def test_refrescar_token_inexistente_lanza_unauthorized() -> None:
    service = _crear_service(FakeUsuarioRepository(), FakeRefreshTokenRepository())

    with pytest.raises(UnauthorizedError):
        await service.refrescar("nunca-emitido")


async def test_refrescar_reuso_detectado_revoca_todo_y_lanza_unauthorized() -> None:
    usuario = CurrentUserResponse(
        id=1, username="ana", nombre_completo="Ana Pérez", roles=[], permisos=[]
    )
    usuario_repositorio = FakeUsuarioRepository({1: usuario})
    refresh_token_repositorio = FakeRefreshTokenRepository()

    token_reusado = "refresh-reusado"
    token_activo = "refresh-todavia-vigente"
    refresh_token_repositorio.agregar(
        RefreshTokenRegistro(
            id=1,
            usuario_id=1,
            token_hash=hashear_refresh_token(token_reusado),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            revoked_at=dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1),
        )
    )
    refresh_token_repositorio.agregar(
        RefreshTokenRegistro(
            id=2,
            usuario_id=1,
            token_hash=hashear_refresh_token(token_activo),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            revoked_at=None,
        )
    )
    service = _crear_service(usuario_repositorio, refresh_token_repositorio)

    with pytest.raises(UnauthorizedError):
        await service.refrescar(token_reusado)

    # Detección de robo: el service revoca también el otro refresh, todavía vigente.
    registro_activo = await refresh_token_repositorio.obtener_por_hash(
        hashear_refresh_token(token_activo)
    )
    assert registro_activo is not None
    assert registro_activo.revoked_at is not None


class _FakeRefreshTokenRepositoryConCarrera(FakeRefreshTokenRepository):
    """Simula que otro request ya rotó/revocó el token entre `validar_refresh` y `rotar`."""

    async def rotar(
        self,
        token_hash_actual: str,
        usuario_id: int,
        token_hash_nuevo: str,
        expires_at_nuevo: dt.datetime,
    ) -> RefreshTokenRegistro | None:
        return None


async def test_refrescar_con_carrera_en_rotar_revoca_todo_y_no_emite_tokens() -> None:
    usuario = CurrentUserResponse(
        id=1, username="ana", nombre_completo="Ana Pérez", roles=[], permisos=[]
    )
    usuario_repositorio = FakeUsuarioRepository({1: usuario})
    refresh_token_repositorio = _FakeRefreshTokenRepositoryConCarrera()
    token = "refresh-en-carrera"
    refresh_token_repositorio.agregar(
        RefreshTokenRegistro(
            id=1,
            usuario_id=1,
            token_hash=hashear_refresh_token(token),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            revoked_at=None,
        )
    )
    service = _crear_service(usuario_repositorio, refresh_token_repositorio)

    with pytest.raises(UnauthorizedError):
        await service.refrescar(token)

    # El token que se intentó rotar queda revocado: el service lo trató como un reuso.
    registro = await refresh_token_repositorio.obtener_por_hash(hashear_refresh_token(token))
    assert registro is not None
    assert registro.revoked_at is not None


async def test_cerrar_sesion_token_vigente_lo_revoca() -> None:
    refresh_token_repositorio = FakeRefreshTokenRepository()
    token = "refresh-a-cerrar"
    refresh_token_repositorio.agregar(
        RefreshTokenRegistro(
            id=1,
            usuario_id=1,
            token_hash=hashear_refresh_token(token),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            revoked_at=None,
        )
    )
    service = _crear_service(FakeUsuarioRepository(), refresh_token_repositorio)

    await service.cerrar_sesion(token)

    registro = await refresh_token_repositorio.obtener_por_hash(hashear_refresh_token(token))
    assert registro is not None
    assert registro.revoked_at is not None


async def test_cerrar_sesion_token_desconocido_es_idempotente() -> None:
    service = _crear_service(FakeUsuarioRepository(), FakeRefreshTokenRepository())

    # No lanza, aunque el token nunca haya existido.
    await service.cerrar_sesion("token-que-no-existe")
