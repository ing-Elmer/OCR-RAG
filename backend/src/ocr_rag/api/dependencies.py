"""Armado de dependencias: único lugar donde se conectan repositorio → validador → service.

Los routers nunca instancian repositorios ni services directamente; solo declaran
`Depends(...)` sobre los providers de este módulo.
"""

from typing import Annotated

from fastapi import Depends, Request
from openai import AsyncOpenAI

from ocr_rag.application.background import BackgroundTaskQueue
from ocr_rag.application.services.auth_service import AuthService
from ocr_rag.application.services.consulta_service import ConsultaService
from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.application.services.health_service import HealthService
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.services.usuario_service import UsuarioService
from ocr_rag.application.validators.auth_validator import AuthValidator
from ocr_rag.application.validators.consulta_validator import ConsultaValidator
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.application.validators.usuario_validator import UsuarioValidator
from ocr_rag.core.clients import (
    ChatClient,
    ClasificadorDocumento,
    EmbeddingClient,
    ExtractorTexto,
    OcrClient,
)
from ocr_rag.core.repositories import (
    DocumentoRepository,
    HealthRepository,
    RefreshTokenRepository,
    UsuarioRepository,
)
from ocr_rag.core.security import PasswordHasher, TokenService
from ocr_rag.core.settings import Settings, get_settings
from ocr_rag.infrastructure.clients.openai_chat_client import OpenAiChatClient
from ocr_rag.infrastructure.clients.openai_clasificador_documento_client import (
    OpenAiClasificadorDocumentoClient,
)
from ocr_rag.infrastructure.clients.openai_embedding_client import OpenAiEmbeddingClient
from ocr_rag.infrastructure.clients.pdf_ocr_extractor_client import PdfOcrExtractorClient
from ocr_rag.infrastructure.clients.tesseract_ocr_client import TesseractOcrClient
from ocr_rag.infrastructure.db import ConnectionFactory
from ocr_rag.infrastructure.repositories.documento_repository import PostgresDocumentoRepository
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


def get_background_queue(request: Request) -> BackgroundTaskQueue:
    """Recupera la cola de tareas en background creada en el `lifespan` de la app."""
    cola: BackgroundTaskQueue = request.app.state.tareas
    return cola


def get_openai_client(request: Request) -> AsyncOpenAI:
    """Recupera el cliente de OpenAI creado una única vez en el `lifespan` de la app."""
    cliente: AsyncOpenAI = request.app.state.openai_client
    return cliente


def get_embedding_client(
    openai_client: Annotated[AsyncOpenAI, Depends(get_openai_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingClient:
    """Provee la implementación concreta de `EmbeddingClient`."""
    return OpenAiEmbeddingClient(openai_client, settings.openai_embedding_model)


def get_chat_client(
    openai_client: Annotated[AsyncOpenAI, Depends(get_openai_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatClient:
    """Provee la implementación concreta de `ChatClient`."""
    return OpenAiChatClient(openai_client, settings.openai_chat_model)


def get_clasificador_documento(
    openai_client: Annotated[AsyncOpenAI, Depends(get_openai_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClasificadorDocumento:
    """Provee la implementación concreta de `ClasificadorDocumento`."""
    return OpenAiClasificadorDocumentoClient(openai_client, settings.openai_chat_model)


def get_ocr_client() -> OcrClient:
    """Provee la implementación concreta de `OcrClient`."""
    return TesseractOcrClient()


def get_extractor_texto(
    ocr_client: Annotated[OcrClient, Depends(get_ocr_client)],
) -> ExtractorTexto:
    """Provee la implementación concreta de `ExtractorTexto`."""
    return PdfOcrExtractorClient(ocr_client)


def get_documento_repository(
    db: Annotated[ConnectionFactory, Depends(get_connection_factory)],
) -> DocumentoRepository:
    """Provee la implementación concreta de `DocumentoRepository`."""
    return PostgresDocumentoRepository(db)


def get_documento_validator(
    repositorio: Annotated[DocumentoRepository, Depends(get_documento_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentoValidator:
    """Arma el validador de documentos con su repositorio y `Settings`."""
    return DocumentoValidator(repositorio, settings)


def get_procesamiento_service(
    repositorio: Annotated[DocumentoRepository, Depends(get_documento_repository)],
    extractor: Annotated[ExtractorTexto, Depends(get_extractor_texto)],
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    clasificador: Annotated[ClasificadorDocumento, Depends(get_clasificador_documento)],
) -> ProcesamientoDocumentoService:
    """Arma el worker de procesamiento OCR + embeddings de un documento."""
    return ProcesamientoDocumentoService(repositorio, extractor, embedding_client, clasificador)


def get_documento_service(
    repositorio: Annotated[DocumentoRepository, Depends(get_documento_repository)],
    validador: Annotated[DocumentoValidator, Depends(get_documento_validator)],
    procesador: Annotated[ProcesamientoDocumentoService, Depends(get_procesamiento_service)],
    cola: Annotated[BackgroundTaskQueue, Depends(get_background_queue)],
) -> DocumentoService:
    """Arma el `DocumentoService` con su repositorio, validador, worker y cola de tareas."""
    return DocumentoService(repositorio, validador, procesador, cola)


def get_consulta_validator(
    repositorio: Annotated[DocumentoRepository, Depends(get_documento_repository)],
) -> ConsultaValidator:
    """Arma el validador de consultas con el repositorio de documentos."""
    return ConsultaValidator(repositorio)


def get_consulta_service(
    repositorio: Annotated[DocumentoRepository, Depends(get_documento_repository)],
    validador: Annotated[ConsultaValidator, Depends(get_consulta_validator)],
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    chat_client: Annotated[ChatClient, Depends(get_chat_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConsultaService:
    """Arma el `ConsultaService` con su repositorio, validador y los clientes de OpenAI."""
    return ConsultaService(repositorio, validador, embedding_client, chat_client, settings)
