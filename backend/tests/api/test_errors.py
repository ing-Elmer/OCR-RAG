"""Tests de los exception handlers (`api/errors.py`).

Usan una app FastAPI mínima, propia del test, que registra los mismos handlers que
`ocr_rag.api.main`: así se prueba la traducción de excepciones sin depender de que exista
un endpoint con body en la app real (este esqueleto todavía no tiene ninguno).
"""

from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import Field

from ocr_rag.api.errors import registrar_manejadores_de_error
from ocr_rag.api.responses import ApiResponse
from ocr_rag.core.exceptions import NotFoundError
from ocr_rag.core.schemas.base import CamelModel


class _EjemploRequest(CamelModel):
    """DTO de prueba, solo para forzar un error de validación de body."""

    nombre: str = Field(min_length=1)


def _crear_app_de_prueba() -> FastAPI:
    """App mínima con los exception handlers reales y dos endpoints de prueba."""
    app = FastAPI()
    registrar_manejadores_de_error(app)

    router = APIRouter()

    @router.post("/ejemplo", response_model=ApiResponse[None])
    async def crear_ejemplo(datos: _EjemploRequest) -> ApiResponse[None]:
        return ApiResponse[None].success("ok")

    @router.get("/ejemplo/{ejemplo_id}", response_model=ApiResponse[None])
    async def obtener_ejemplo(ejemplo_id: int) -> ApiResponse[None]:
        raise NotFoundError(f"No existe el ejemplo {ejemplo_id}")

    app.include_router(router)
    return app


async def test_body_invalido_devuelve_400_con_errores_por_campo() -> None:
    app = _crear_app_de_prueba()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        respuesta = await client.post("/ejemplo", json={"nombre": ""})

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "Error"
    assert "nombre" in cuerpo["errors"]


async def test_excepcion_de_dominio_devuelve_su_status_code() -> None:
    app = _crear_app_de_prueba()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        respuesta = await client.get("/ejemplo/99")

    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "Error"
    assert cuerpo["message"] == "No existe el ejemplo 99"
