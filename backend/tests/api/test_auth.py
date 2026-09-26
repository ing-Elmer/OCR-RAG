"""Tests del router de autenticación (`POST /api/auth/{login,refresh,logout}`)."""

import datetime as dt

from httpx import AsyncClient

from ocr_rag.core.refresh_tokens import hashear_refresh_token
from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from tests.conftest import CONTRASENA_DE_PRUEBA, FakeRefreshTokenRepository


async def test_login_credenciales_correctas_devuelve_200_con_los_tokens(
    async_client: AsyncClient,
) -> None:
    respuesta = await async_client.post(
        "/api/auth/login", json={"username": "ana", "password": CONTRASENA_DE_PRUEBA}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "Success"
    assert cuerpo["data"]["accessToken"]
    assert cuerpo["data"]["refreshToken"]
    assert cuerpo["data"]["tokenType"] == "bearer"
    assert cuerpo["data"]["expiresIn"] > 0


async def test_login_password_incorrecto_devuelve_401(async_client: AsyncClient) -> None:
    respuesta = await async_client.post(
        "/api/auth/login", json={"username": "ana", "password": "password-incorrecto"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["message"] == "Usuario o contraseña incorrectos"


async def test_login_usuario_inexistente_devuelve_401_con_el_mismo_mensaje(
    async_client: AsyncClient,
) -> None:
    respuesta = await async_client.post(
        "/api/auth/login", json={"username": "no-existe", "password": "cualquier-password"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["message"] == "Usuario o contraseña incorrectos"


async def test_login_usuario_inactivo_devuelve_401_con_el_mismo_mensaje(
    async_client: AsyncClient,
) -> None:
    # Ningún usuario "inactivo" está cargado en el fake: el repositorio real ya filtra por
    # `activo = true`, así que para el validador es indistinguible de "no existe".
    respuesta = await async_client.post(
        "/api/auth/login", json={"username": "inactivo", "password": CONTRASENA_DE_PRUEBA}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["message"] == "Usuario o contraseña incorrectos"


async def test_login_body_invalido_devuelve_400(async_client: AsyncClient) -> None:
    respuesta = await async_client.post("/api/auth/login", json={"username": "", "password": ""})

    assert respuesta.status_code == 400
    assert respuesta.json()["status"] == "Error"


async def test_refresh_token_vigente_devuelve_200_y_rota(
    async_client: AsyncClient,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
) -> None:
    token_viejo = "refresh-vigente-de-test"
    await fake_refresh_token_repository.crear(
        usuario_id=1,
        token_hash=hashear_refresh_token(token_viejo),
        expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    )

    respuesta = await async_client.post("/api/auth/refresh", json={"refreshToken": token_viejo})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()["data"]
    assert cuerpo["refreshToken"] != token_viejo

    registro_viejo = await fake_refresh_token_repository.obtener_por_hash(
        hashear_refresh_token(token_viejo)
    )
    assert registro_viejo is not None
    assert registro_viejo.revoked_at is not None


async def test_refresh_token_vencido_devuelve_401(
    async_client: AsyncClient,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
) -> None:
    token = "refresh-vencido-de-test"
    fake_refresh_token_repository.agregar(
        RefreshTokenRegistro(
            id=99,
            usuario_id=1,
            token_hash=hashear_refresh_token(token),
            expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1),
            revoked_at=None,
        )
    )

    respuesta = await async_client.post("/api/auth/refresh", json={"refreshToken": token})

    assert respuesta.status_code == 401


async def test_refresh_token_inexistente_devuelve_401(async_client: AsyncClient) -> None:
    respuesta = await async_client.post("/api/auth/refresh", json={"refreshToken": "nunca-emitido"})

    assert respuesta.status_code == 401


async def test_refresh_reuso_de_token_revocado_devuelve_401_y_revoca_todos(
    async_client: AsyncClient,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
) -> None:
    token_reusado = "refresh-ya-revocado-de-test"
    token_activo = "otro-refresh-vigente-de-test"
    fake_refresh_token_repository.agregar(
        RefreshTokenRegistro(
            id=1,
            usuario_id=1,
            token_hash=hashear_refresh_token(token_reusado),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            revoked_at=dt.datetime.now(dt.UTC) - dt.timedelta(minutes=5),
        )
    )
    fake_refresh_token_repository.agregar(
        RefreshTokenRegistro(
            id=2,
            usuario_id=1,
            token_hash=hashear_refresh_token(token_activo),
            expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            revoked_at=None,
        )
    )

    respuesta = await async_client.post("/api/auth/refresh", json={"refreshToken": token_reusado})

    assert respuesta.status_code == 401
    registro_activo = await fake_refresh_token_repository.obtener_por_hash(
        hashear_refresh_token(token_activo)
    )
    assert registro_activo is not None
    assert registro_activo.revoked_at is not None


async def test_logout_token_vigente_devuelve_200_y_lo_revoca(
    async_client: AsyncClient,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
) -> None:
    token = "refresh-para-logout"
    await fake_refresh_token_repository.crear(
        usuario_id=1,
        token_hash=hashear_refresh_token(token),
        expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    )

    respuesta = await async_client.post("/api/auth/logout", json={"refreshToken": token})

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "Success"
    registro = await fake_refresh_token_repository.obtener_por_hash(hashear_refresh_token(token))
    assert registro is not None
    assert registro.revoked_at is not None


async def test_logout_token_desconocido_es_idempotente_y_devuelve_200(
    async_client: AsyncClient,
) -> None:
    respuesta = await async_client.post(
        "/api/auth/logout", json={"refreshToken": "token-que-no-existe"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "Success"
