"""Tests del `AuthValidator`."""

import datetime as dt

import pytest

from ocr_rag.application.validators.auth_validator import (
    MENSAJE_REFRESH_INVALIDO,
    AuthValidator,
)
from ocr_rag.core.exceptions import RefreshTokenReusadoError, UnauthorizedError
from ocr_rag.core.refresh_tokens import hashear_refresh_token
from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales
from tests.conftest import (
    CONTRASENA_DE_PRUEBA,
    FakePasswordHasher,
    FakeRefreshTokenRepository,
    FakeUsuarioRepository,
)


def _crear_validador(
    usuario_repositorio: FakeUsuarioRepository,
    refresh_token_repositorio: FakeRefreshTokenRepository,
) -> AuthValidator:
    return AuthValidator(usuario_repositorio, refresh_token_repositorio, FakePasswordHasher())


async def test_validar_login_credenciales_correctas_devuelve_las_credenciales() -> None:
    credenciales = UsuarioCredenciales(
        id=1,
        username="ana",
        password_hash=FakePasswordHasher.hashear_para_test(CONTRASENA_DE_PRUEBA),
    )
    usuario_repositorio = FakeUsuarioRepository(credenciales={"ana": credenciales})
    validador = _crear_validador(usuario_repositorio, FakeRefreshTokenRepository())

    resultado = await validador.validar_login("ana", CONTRASENA_DE_PRUEBA)

    assert resultado == credenciales


async def test_validar_login_password_incorrecto_lanza_unauthorized_con_mensaje_generico() -> None:
    credenciales = UsuarioCredenciales(
        id=1,
        username="ana",
        password_hash=FakePasswordHasher.hashear_para_test(CONTRASENA_DE_PRUEBA),
    )
    usuario_repositorio = FakeUsuarioRepository(credenciales={"ana": credenciales})
    validador = _crear_validador(usuario_repositorio, FakeRefreshTokenRepository())

    with pytest.raises(UnauthorizedError) as info:
        await validador.validar_login("ana", "password-incorrecto")

    assert info.value.message == "Usuario o contraseña incorrectos"


async def test_validar_login_username_inexistente_lanza_unauthorized_con_mismo_mensaje() -> None:
    usuario_repositorio = FakeUsuarioRepository()
    validador = _crear_validador(usuario_repositorio, FakeRefreshTokenRepository())

    with pytest.raises(UnauthorizedError) as info:
        await validador.validar_login("no-existe", "cualquier-password")

    assert info.value.message == "Usuario o contraseña incorrectos"


async def test_validar_login_usuario_inactivo_lanza_unauthorized_con_mismo_mensaje() -> None:
    # El repositorio (real) filtra `activo = true`; un usuario inactivo no aparece en
    # `obtener_credenciales_activas`, así que el fake lo simula no incluyéndolo.
    usuario_repositorio = FakeUsuarioRepository()
    validador = _crear_validador(usuario_repositorio, FakeRefreshTokenRepository())

    with pytest.raises(UnauthorizedError) as info:
        await validador.validar_login("inactivo", CONTRASENA_DE_PRUEBA)

    assert info.value.message == "Usuario o contraseña incorrectos"


async def test_validar_refresh_token_vigente_devuelve_el_registro() -> None:
    usuario = CurrentUserResponse(
        id=1, username="ana", nombre_completo="Ana Pérez", roles=[], permisos=[]
    )
    usuario_repositorio = FakeUsuarioRepository({1: usuario})
    refresh_token_repositorio = FakeRefreshTokenRepository()
    token = "token-vigente"
    registro = RefreshTokenRegistro(
        id=1,
        usuario_id=1,
        token_hash=hashear_refresh_token(token),
        expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        revoked_at=None,
    )
    refresh_token_repositorio.agregar(registro)
    validador = _crear_validador(usuario_repositorio, refresh_token_repositorio)

    resultado = await validador.validar_refresh(token)

    assert resultado == registro


async def test_validar_refresh_token_inexistente_lanza_unauthorized() -> None:
    validador = _crear_validador(FakeUsuarioRepository(), FakeRefreshTokenRepository())

    with pytest.raises(UnauthorizedError) as info:
        await validador.validar_refresh("token-nunca-emitido")

    assert info.value.message == MENSAJE_REFRESH_INVALIDO


async def test_validar_refresh_token_vencido_lanza_unauthorized() -> None:
    usuario = CurrentUserResponse(
        id=1, username="ana", nombre_completo="Ana Pérez", roles=[], permisos=[]
    )
    usuario_repositorio = FakeUsuarioRepository({1: usuario})
    refresh_token_repositorio = FakeRefreshTokenRepository()
    token = "token-vencido"
    refresh_token_repositorio.agregar(
        RefreshTokenRegistro(
            id=1,
            usuario_id=1,
            token_hash=hashear_refresh_token(token),
            expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1),
            revoked_at=None,
        )
    )
    validador = _crear_validador(usuario_repositorio, refresh_token_repositorio)

    with pytest.raises(UnauthorizedError) as info:
        await validador.validar_refresh(token)

    assert info.value.message == MENSAJE_REFRESH_INVALIDO


async def test_validar_refresh_usuario_inactivo_lanza_unauthorized() -> None:
    usuario_repositorio = FakeUsuarioRepository()  # el usuario 1 no está (inactivo/inexistente)
    refresh_token_repositorio = FakeRefreshTokenRepository()
    token = "token-de-usuario-inactivo"
    refresh_token_repositorio.agregar(
        RefreshTokenRegistro(
            id=1,
            usuario_id=1,
            token_hash=hashear_refresh_token(token),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            revoked_at=None,
        )
    )
    validador = _crear_validador(usuario_repositorio, refresh_token_repositorio)

    with pytest.raises(UnauthorizedError):
        await validador.validar_refresh(token)


async def test_validar_refresh_token_revocado_lanza_reusado_sin_revocar_nada() -> None:
    usuario = CurrentUserResponse(
        id=1, username="ana", nombre_completo="Ana Pérez", roles=[], permisos=[]
    )
    usuario_repositorio = FakeUsuarioRepository({1: usuario})
    refresh_token_repositorio = FakeRefreshTokenRepository()

    token_reusado = "token-ya-revocado"
    token_activo = "otro-token-del-mismo-usuario"
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
    validador = _crear_validador(usuario_repositorio, refresh_token_repositorio)

    with pytest.raises(RefreshTokenReusadoError) as info:
        await validador.validar_refresh(token_reusado)

    assert info.value.message == MENSAJE_REFRESH_INVALIDO
    assert info.value.usuario_id == 1
    # El validador solo detecta: no escribe en la base. El otro refresh sigue vigente; la
    # revocación de toda la sesión es responsabilidad del `AuthService`.
    registro_activo = await refresh_token_repositorio.obtener_por_hash(
        hashear_refresh_token(token_activo)
    )
    assert registro_activo is not None
    assert registro_activo.revoked_at is None
