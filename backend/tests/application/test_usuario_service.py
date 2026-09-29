"""Tests del `UsuarioService`."""

import pytest

from ocr_rag.application.services.usuario_service import UsuarioService
from ocr_rag.application.validators.usuario_validator import UsuarioValidator
from ocr_rag.core.exceptions import NotFoundError
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales


class _FakeUsuarioRepository:
    """Implementación en memoria de `UsuarioRepository`, para este test."""

    def __init__(self, usuarios: dict[int, CurrentUserResponse]) -> None:
        self._usuarios = usuarios

    async def obtener_usuario_actual(self, usuario_id: int) -> CurrentUserResponse | None:
        return self._usuarios.get(usuario_id)

    async def obtener_credenciales_activas(self, username: str) -> UsuarioCredenciales | None:
        raise NotImplementedError("No lo usa este test")

    async def existe_username(self, username: str) -> bool:
        raise NotImplementedError("No lo usa este test")

    async def crear(self, username: str, password_hash: str, nombre_completo: str) -> int:
        raise NotImplementedError("No lo usa este test")

    async def asignar_rol(self, usuario_id: int, rol_codigo: str) -> None:
        raise NotImplementedError("No lo usa este test")


def _crear_service(usuarios: dict[int, CurrentUserResponse]) -> UsuarioService:
    repositorio = _FakeUsuarioRepository(usuarios)
    return UsuarioService(repositorio, UsuarioValidator(repositorio))


async def test_obtener_usuario_actual_usuario_existente_devuelve_sus_datos() -> None:
    usuario = CurrentUserResponse(
        id=1, username="ana", nombre_completo="Ana Pérez", roles=["ADMIN"], permisos=[]
    )
    service = _crear_service({1: usuario})

    resultado = await service.obtener_usuario_actual(1)

    assert resultado == usuario


async def test_obtener_usuario_actual_usuario_inexistente_lanza_not_found() -> None:
    service = _crear_service({})

    with pytest.raises(NotFoundError):
        await service.obtener_usuario_actual(99)
