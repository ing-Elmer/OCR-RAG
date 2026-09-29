"""Armado de dependencias: único lugar donde se conectan repositorio → validador → service.

Los routers nunca instancian repositorios ni services directamente; solo declaran
`Depends(...)` sobre los providers de este módulo.
"""

from typing import Annotated

from fastapi import Depends, Request

from ocr_rag.application.services.auth_service import AuthService
from ocr_rag.application.services.health_service import HealthService
from ocr_rag.application.services.usuario_service import UsuarioService
from ocr_rag.application.validators.auth_validator import AuthValidator
from ocr_rag.application.validators.usuario_validator import UsuarioValidator
from ocr_rag.core.repositories import HealthRepository, RefreshTokenRepository, UsuarioRepository
from ocr_rag.core.security import PasswordHasher, TokenService
from ocr_rag.core.settings import Settings, get_settings
from ocr_rag.infrastructure.db import ConnectionFactory
from ocr_rag.infrastructure.repositories.health_repository import PostgresHealthRepository
from ocr_rag.infrastructure.repositories.refresh_token_repository import (
    PostgresRefreshTokenRepository,
)
from ocr_rag.infrastructure.repositories.usuario_repository import PostgresUsuarioRepository
from ocr_rag.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from ocr_rag.infrastructure.security.jwt_token_service import JwtTokenService


def get_connection_factory(request: Request) -> ConnectionFactory:
    """Recupera la fábrica de conexiones creada en el `lifespan` de la app."""
    factory: ConnectionFactory = request.app.state.connection_factory
    return factory


def get_health_repository(
    db: Annotated[ConnectionFactory, Depends(get_connection_factory)],
) -> HealthRepository:
    """Provee la implementación concreta de `HealthRepository`."""
    return PostgresHealthRepository(db)


def get_health_service(
    repositorio: Annotated[HealthRepository, Depends(get_health_repository)],
) -> HealthService:
    """Arma el `HealthService` con su repositorio."""
    return HealthService(repositorio)


def get_usuario_repository(
    db: Annotated[ConnectionFactory, Depends(get_connection_factory)],
) -> UsuarioRepository:
    """Provee la implementación concreta de `UsuarioRepository`."""
    return PostgresUsuarioRepository(db)


def get_usuario_validator(
    repositorio: Annotated[UsuarioRepository, Depends(get_usuario_repository)],
) -> UsuarioValidator:
    """Arma el validador de usuarios con su repositorio."""
    return UsuarioValidator(repositorio)


def get_usuario_service(
    repositorio: Annotated[UsuarioRepository, Depends(get_usuario_repository)],
    validador: Annotated[UsuarioValidator, Depends(get_usuario_validator)],
) -> UsuarioService:
    """Arma el `UsuarioService` con su repositorio y validador."""
    return UsuarioService(repositorio, validador)


def get_refresh_token_repository(
    db: Annotated[ConnectionFactory, Depends(get_connection_factory)],
) -> RefreshTokenRepository:
    """Provee la implementación concreta de `RefreshTokenRepository`."""
    return PostgresRefreshTokenRepository(db)


def get_password_hasher() -> PasswordHasher:
    """Provee la implementación concreta de `PasswordHasher`."""
    return BcryptPasswordHasher()


def get_token_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenService:
    """Provee la implementación concreta de `TokenService`."""
    return JwtTokenService(settings)


def get_auth_validator(
    usuario_repositorio: Annotated[UsuarioRepository, Depends(get_usuario_repository)],
    refresh_token_repositorio: Annotated[
        RefreshTokenRepository, Depends(get_refresh_token_repository)
    ],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
) -> AuthValidator:
    """Arma el validador de autenticación con sus repositorios y el hasher de contraseñas."""
    return AuthValidator(usuario_repositorio, refresh_token_repositorio, password_hasher)


def get_auth_service(
    refresh_token_repositorio: Annotated[
        RefreshTokenRepository, Depends(get_refresh_token_repository)
    ],
    validador: Annotated[AuthValidator, Depends(get_auth_validator)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    """Arma el `AuthService` con su repositorio, validador, `TokenService` y `Settings`."""
    return AuthService(refresh_token_repositorio, validador, token_service, settings)
