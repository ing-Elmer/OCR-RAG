"""Tests del router de documentos (`/api/documentos`)."""

import datetime as dt

import jwt
from httpx import AsyncClient

from ocr_rag.core.schemas.usuario import CurrentUserResponse
from ocr_rag.core.settings import get_settings
from tests.conftest import FakeDocumentoRepository, FakeUsuarioRepository


def _crear_token(usuario_id: int) -> str:
    """Firma un JWT de prueba con la misma clave que usa la app en los tests."""
    settings = get_settings()
    claims = {
        "sub": str(usuario_id),
        "type": "access",
        "exp": dt.datetime.now(dt.UTC) + dt.timedelta(minutes=30),
    }
    return jwt.encode(
        claims, settings.jwt_signing_key.get_secret_value(), algorithm=settings.jwt_algorithm
    )


async def test_cargar_documento_valido_devuelve_201(async_client: AsyncClient) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/documentos",
        headers={"Authorization": f"Bearer {token}"},
        files={"archivo": ("factura.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "Created"
    assert cuerpo["data"]["nombreArchivo"] == "factura.pdf"
    assert cuerpo["data"]["estado"] == "pendiente"


async def test_cargar_documento_con_tipo_no_permitido_devuelve_400(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/documentos",
        headers={"Authorization": f"Bearer {token}"},
        files={"archivo": ("documento.docx", b"contenido", "application/msword")},
    )

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "Error"
    assert "archivo" in cuerpo["errors"]


async def test_cargar_documento_con_idioma_invalido_devuelve_400(async_client: AsyncClient) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/documentos",
        headers={"Authorization": f"Bearer {token}"},
        files={"archivo": ("a.pdf", b"%PDF-1.4 contenido", "application/pdf")},
        data={"idioma": "ESPANOL"},
    )

    assert respuesta.status_code == 400
    assert "idioma" in respuesta.json()["errors"]


async def test_cargar_documento_sin_permiso_devuelve_403(
    async_client: AsyncClient, fake_usuario_repository: FakeUsuarioRepository
) -> None:
    fake_usuario_repository.agregar(
        CurrentUserResponse(
            id=2, username="sin-permisos", nombre_completo="Sin Permisos", roles=[], permisos=[]
        )
    )
    token = _crear_token(2)

    respuesta = await async_client.post(
        "/api/documentos",
        headers={"Authorization": f"Bearer {token}"},
        files={"archivo": ("a.pdf", b"%PDF-1.4 contenido", "application/pdf")},
    )

    assert respuesta.status_code == 403


async def test_cargar_documento_sin_token_devuelve_401(async_client: AsyncClient) -> None:
    respuesta = await async_client.post(
        "/api/documentos",
        files={"archivo": ("a.pdf", b"%PDF-1.4 contenido", "application/pdf")},
    )

    assert respuesta.status_code == 401


async def test_listar_documentos_devuelve_meta_de_paginacion(
    async_client: AsyncClient, fake_documento_repository: FakeDocumentoRepository
) -> None:
    for indice in range(3):
        await fake_documento_repository.crear(
            nombre_archivo=f"doc-{indice}.pdf",
            tipo_contenido="application/pdf",
            tamano_bytes=10,
            idioma="spa",
            creado_por_id=1,
            contenido=b"contenido",
            sha256="a" * 64,
        )
    token = _crear_token(1)

    respuesta = await async_client.get(
        "/api/documentos", headers={"Authorization": f"Bearer {token}"}, params={"limite": 2}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["data"]) == 2
    assert cuerpo["meta"] == {"total": 3, "limite": 2, "offset": 0}


async def test_listar_documentos_sin_token_devuelve_401(async_client: AsyncClient) -> None:
    respuesta = await async_client.get("/api/documentos")

    assert respuesta.status_code == 401


async def test_obtener_documento_inexistente_devuelve_404(async_client: AsyncClient) -> None:
    token = _crear_token(1)

    respuesta = await async_client.get(
        "/api/documentos/999", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 404


async def test_obtener_documento_existente_devuelve_200(
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
    token = _crear_token(1)

    respuesta = await async_client.get(
        f"/api/documentos/{documento_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["id"] == documento_id


async def test_cargar_documento_con_tipo_documento_valido_lo_asigna(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/documentos",
        headers={"Authorization": f"Bearer {token}"},
        files={"archivo": ("contrato.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")},
        data={"tipoDocumento": "contrato"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["data"]["tipoDocumento"] == "contrato"


async def test_cargar_documento_sin_tipo_documento_queda_otro_hasta_clasificar(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/documentos",
        headers={"Authorization": f"Bearer {token}"},
        files={"archivo": ("a.pdf", b"%PDF-1.4 contenido de prueba", "application/pdf")},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["data"]["tipoDocumento"] == "otro"
    assert respuesta.json()["data"]["norma"] is None


async def test_cargar_documento_con_tipo_documento_invalido_devuelve_400(
    async_client: AsyncClient,
) -> None:
    token = _crear_token(1)

    respuesta = await async_client.post(
        "/api/documentos",
        headers={"Authorization": f"Bearer {token}"},
        files={"archivo": ("a.pdf", b"%PDF-1.4 contenido", "application/pdf")},
        data={"tipoDocumento": "factura"},
    )

    assert respuesta.status_code == 400
    assert "tipoDocumento" in respuesta.json()["errors"]


async def test_actualizar_documento_valido_devuelve_200(
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
    token = _crear_token(1)

    respuesta = await async_client.patch(
        f"/api/documentos/{documento_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"tipoDocumento": "normativa", "norma": "CAUCA IV"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()["data"]
    assert cuerpo["tipoDocumento"] == "normativa"
    assert cuerpo["norma"] == "CAUCA IV"


async def test_actualizar_documento_norma_null_la_limpia(
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
        tipo_documento="normativa",
        norma="CAUCA IV",
    )
    token = _crear_token(1)

    respuesta = await async_client.patch(
        f"/api/documentos/{documento_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"norma": None},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["norma"] is None
    assert respuesta.json()["data"]["tipoDocumento"] == "normativa"


async def test_actualizar_documento_body_vacio_devuelve_400(
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
    token = _crear_token(1)

    respuesta = await async_client.patch(
        f"/api/documentos/{documento_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )

    assert respuesta.status_code == 400


async def test_actualizar_documento_tipo_invalido_devuelve_400(
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
    token = _crear_token(1)

    respuesta = await async_client.patch(
        f"/api/documentos/{documento_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"tipoDocumento": "factura"},
    )

    assert respuesta.status_code == 400


async def test_actualizar_documento_inexistente_devuelve_404(async_client: AsyncClient) -> None:
    token = _crear_token(1)

    respuesta = await async_client.patch(
        "/api/documentos/999",
        headers={"Authorization": f"Bearer {token}"},
        json={"tipoDocumento": "contrato"},
    )

    assert respuesta.status_code == 404


async def test_actualizar_documento_sin_permiso_devuelve_403(
    async_client: AsyncClient,
    fake_documento_repository: FakeDocumentoRepository,
    fake_usuario_repository: FakeUsuarioRepository,
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
    fake_usuario_repository.agregar(
        CurrentUserResponse(
            id=2, username="sin-permisos", nombre_completo="Sin Permisos", roles=[], permisos=[]
        )
    )
    token = _crear_token(2)

    respuesta = await async_client.patch(
        f"/api/documentos/{documento_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"tipoDocumento": "contrato"},
    )

    assert respuesta.status_code == 403


async def test_actualizar_documento_sin_token_devuelve_401(async_client: AsyncClient) -> None:
    respuesta = await async_client.patch("/api/documentos/1", json={"tipoDocumento": "contrato"})

    assert respuesta.status_code == 401
