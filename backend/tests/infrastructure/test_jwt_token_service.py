"""Tests del `JwtTokenService`."""

import datetime as dt

import jwt
import pytest

from ocr_rag.core.exceptions import UnauthorizedError
from ocr_rag.core.settings import get_settings
from ocr_rag.infrastructure.security.jwt_token_service import JwtTokenService


def _crear_service() -> JwtTokenService:
    return JwtTokenService(get_settings())


def test_crear_access_token_y_decodificarlo_devuelve_el_usuario_id() -> None:
    service = _crear_service()

    token = service.crear_access_token(42)

    assert service.decodificar_access_token(token) == 42


def test_decodificar_access_token_con_firma_invalida_lanza_unauthorized() -> None:
    service = _crear_service()
    token = jwt.encode(
        {"sub": "1", "type": "access", "exp": dt.datetime.now(dt.UTC) + dt.timedelta(minutes=5)},
        "otra-clave-de-firma-completamente-distinta-y-larga",
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        service.decodificar_access_token(token)


def test_decodificar_access_token_expirado_lanza_unauthorized() -> None:
    settings = get_settings()
    service = JwtTokenService(settings)
    token = jwt.encode(
        {
            "sub": "1",
            "type": "access",
            "exp": dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1),
        },
        settings.jwt_signing_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError):
        service.decodificar_access_token(token)


def test_decodificar_access_token_con_type_distinto_de_access_lanza_unauthorized() -> None:
    settings = get_settings()
    service = JwtTokenService(settings)
    token = jwt.encode(
        {
            "sub": "1",
            "type": "refresh",
            "exp": dt.datetime.now(dt.UTC) + dt.timedelta(minutes=5),
        },
        settings.jwt_signing_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError):
        service.decodificar_access_token(token)
