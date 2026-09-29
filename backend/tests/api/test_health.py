"""Tests de `GET /health`."""

from httpx import AsyncClient


async def test_obtener_salud_devuelve_200_y_envelope(async_client: AsyncClient) -> None:
    respuesta = await async_client.get("/health")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "Success"
    assert cuerpo["data"] == {"status": "ok", "database": "ok", "version": "0.1.0"}
    assert cuerpo["errors"] is None
