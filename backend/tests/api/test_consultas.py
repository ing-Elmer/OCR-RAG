"""Tests del router de consultas (`/api/consultas`)."""

import datetime as dt

import jwt
from httpx import AsyncClient

from ocr_rag.core.schemas.usuario import CurrentUserResponse
from ocr_rag.core.settings import get_settings
from tests.conftest import FakeDocumentoRepository, FakeUsuarioRepository


def _crear_token(usuario_id: int) -> str:
    settings = get_settings()
    claims = {
        "sub": str(usuario_id),
        "type": "access",
        "exp": dt.datetime.now(dt.UTC) + dt.timedelta(minutes=30),
    }
    return jwt.encode(
        claims, settings.jwt_signing_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


async def test_realizar_consulta_sin_resultados_devuelve_200_sin_fuentes(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/consultas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pregunta": "¿Qué dice el documento?"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()["data"]
    assert cuerpo["fuentes"] == []
    assert cuerpo["respuesta"] == "No encontré información relevante en los documentos cargados."


async def test_realizar_consulta_con_documento_ids_invalidos_devuelve_400(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/consultas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pregunta": "¿Qué dice el documento?", "documentoIds": [999]},
    )

    assert respuesta.status_code == 400
    assert "documentoIds" in respuesta.json()["errors"]


async def test_realizar_consulta_body_invalido_devuelve_400(async_client: AsyncClient) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/consultas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pregunta": "a"},
    )

    assert respuesta.status_code == 400


async def test_realizar_consulta_sin_permiso_devuelve_403(
    async_client: AsyncClient, fake_usuario_repository: FakeUsuarioRepository
) -> None:
    fake_usuario_repository.agregar(
        CurrentUserResponse(
            id=2, username="sin-permisos", nombre_completo="Sin Permisos", roles=[], permisos=[]
        )
    )
    token = _crear_token(2)

    respuesta = await async_client.post(
        "/api/consultas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pregunta": "¿Qué dice el documento?"},
    )

    assert respuesta.status_code == 403


async def test_realizar_consulta_sin_token_devuelve_401(async_client: AsyncClient) -> None:
    respuesta = await async_client.post("/api/consultas", json={"pregunta": "¿Qué dice?"})

    assert respuesta.status_code == 401


async def test_realizar_consulta_top_k_mayor_al_maximo_devuelve_400(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/consultas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pregunta": "¿Qué dice el documento?", "topK": 21},
    )

    assert respuesta.status_code == 400


async def test_realizar_consulta_con_tipos_documento_invalido_devuelve_400(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/consultas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pregunta": "¿Qué dice el documento?", "tiposDocumento": ["factura"]},
    )

    assert respuesta.status_code == 400


async def test_realizar_consulta_con_documento_procesado_devuelve_200(
    async_client: AsyncClient, fake_documento_repository: FakeDocumentoRepository
) -> None:
    documento_id = await fake_documento_repository.crear(
        nombre_archivo="a.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256="a" * 64,
    )
    tomado = await fake_documento_repository.tomar_para_procesar(documento_id)
    assert tomado is not None
    await fake_documento_repository.guardar_resultado(
        documento_id, paginas=1, chunks=[], version_procesamiento=tomado.version_procesamiento
    )
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/consultas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pregunta": "¿Qué dice el documento?", "documentoIds": [documento_id]},
    )

    assert respuesta.status_code == 200
