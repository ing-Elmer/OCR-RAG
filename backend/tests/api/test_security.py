"""Tests de autenticación y autorización (`api/security.py`)."""

import datetime as dt

import jwt
import pytest
from httpx import AsyncClient

from ocr_rag.api.security import require_permission
from ocr_rag.core.current_user import CurrentUser
from ocr_rag.core.exceptions import ForbiddenError
from ocr_rag.core.settings import get_settings


def _crear_token(usuario_id: int, *, expirado: bool = False, tipo: str = "access") -> str:
    """Firma un JWT de prueba con la misma clave que usa la app en los tests."""
    settings = get_settings()
    delta = dt.timedelta(minutes=-5) if expirado else dt.timedelta(minutes=30)
    claims = {"sub": str(usuario_id), "type": tipo, "exp": dt.datetime.now(dt.UTC) + delta}
    return jwt.encode(
        claims, settings.jwt_signing_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


async def test_obtener_usuario_actual_sin_token_devuelve_401(async_client: AsyncClient) -> None:
    respuesta = await async_client.get("/api/me")

    assert respuesta.status_code == 401
    assert respuesta.json()["status"] == "Error"


async def test_obtener_usuario_actual_con_token_invalido_devuelve_401(
    async_client: AsyncClient,
) -> None:
    respuesta = await async_client.get(
        "/api/me", headers={"Authorization": "Bearer token-invalido"}
    )

    assert respuesta.status_code == 401


async def test_obtener_usuario_actual_con_token_expirado_devuelve_401(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1, expirado=True)

    respuesta = await async_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401


async def test_obtener_usuario_actual_con_token_valido_devuelve_200(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["username"] == "ana"


async def test_obtener_usuario_actual_con_token_que_no_es_de_tipo_access_devuelve_401(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1, tipo="refresh")

    respuesta = await async_client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401


def test_require_permission_sin_el_permiso_lanza_forbidden() -> None:
    usuario = CurrentUser(id=1, username="ana", nombre_completo="Ana Pérez", permisos=[])
    verificar = require_permission("DOCUMENTO_VER")

    with pytest.raises(ForbiddenError):
        verificar(usuario)


def test_require_permission_con_el_permiso_devuelve_el_usuario() -> None:
    usuario = CurrentUser(
        id=1, username="ana", nombre_completo="Ana Pérez", permisos=["DOCUMENTO_VER"]
    )
    verificar = require_permission("DOCUMENTO_VER")

    assert verificar(usuario) is usuario
