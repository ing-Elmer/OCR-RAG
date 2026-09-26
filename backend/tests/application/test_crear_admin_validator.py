"""Tests del `CrearAdminValidator`."""

import pytest

from ocr_rag.application.validators.crear_admin_validator import CrearAdminValidator
from ocr_rag.core.exceptions import ValidationError
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales


class _FakeUsuarioRepository:
    """Implementación en memoria de `UsuarioRepository`, para este test."""

    def __init__(self, usernames_existentes: set[str] | None = None) -> None:
        self._usernames_existentes = usernames_existentes or set()

    async def obtener_usuario_actual(self, usuario_id: int) -> CurrentUserResponse | None:
        raise NotImplementedError("No lo usa este test")

    async def obtener_credenciales_activas(self, username: str) -> UsuarioCredenciales | None:
        raise NotImplementedError("No lo usa este test")

    async def existe_username(self, username: str) -> bool:
        return username in self._usernames_existentes

    async def crear(self, username: str, password_hash: str, nombre_completo: str) -> int:
        raise NotImplementedError("No lo usa este test")

    async def asignar_rol(self, usuario_id: int, rol_codigo: str) -> None:
        raise NotImplementedError("No lo usa este test")


async def test_validar_username_disponible_y_password_larga_no_lanza() -> None:
    validador = CrearAdminValidator(_FakeUsuarioRepository())

    await validador.validar("nuevo-admin", "una-contraseña-larga-123")


async def test_validar_username_duplicado_lanza_validation_error() -> None:
    validador = CrearAdminValidator(_FakeUsuarioRepository({"ana"}))

    with pytest.raises(ValidationError) as info:
        await validador.validar("ana", "una-contraseña-larga-123")

    assert "username" in (info.value.errors or {})


async def test_validar_password_corta_lanza_validation_error() -> None:
    validador = CrearAdminValidator(_FakeUsuarioRepository())

    with pytest.raises(ValidationError) as info:
        await validador.validar("nuevo-admin", "corta")

    assert "password" in (info.value.errors or {})
