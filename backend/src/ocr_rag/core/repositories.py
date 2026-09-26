"""Interfaces (`Protocol`) de los repositorios: las implementa `infrastructure`."""

from datetime import datetime
from typing import Protocol

from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.core.schemas.documento import (
    ChunkParaGuardar,
    ChunkSimilar,
    DocumentoParaProcesar,
    DocumentoResponse,
)
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales


class HealthRepository(Protocol):
    """Verifica el estado de la conexión principal a la base de datos."""

    async def verificar_conexion(self) -> bool:
        """Ejecuta un `SELECT 1` contra la conexión principal y devuelve si respondió."""
        ...


class UsuarioRepository(Protocol):
    """Acceso a los datos de usuarios, roles y permisos."""

    async def obtener_usuario_actual(self, usuario_id: int) -> CurrentUserResponse | None:
        """Devuelve el usuario activo con sus roles y permisos, o `None` si no existe."""
        ...

    async def obtener_credenciales_activas(self, username: str) -> UsuarioCredenciales | None:
        """Devuelve `id`, `username` y `password_hash` si el usuario existe y está activo."""
        ...

    async def existe_username(self, username: str) -> bool:
        """Indica si ya existe un usuario (activo o no) con ese `username`."""
        ...

    async def crear(self, username: str, password_hash: str, nombre_completo: str) -> int:
        """Crea un usuario activo y devuelve su id."""
        ...

    async def asignar_rol(self, usuario_id: int, rol_codigo: str) -> None:
        """Asigna el rol `rol_codigo` al usuario. Lanza `NotFoundError` si el rol no existe."""
        ...


class RefreshTokenRepository(Protocol):
    """Acceso a los refresh tokens emitidos: rotativos, opacos, guardados hasheados."""

    async def crear(
        self, usuario_id: int, token_hash: str, expires_at: datetime
    ) -> RefreshTokenRegistro:
        """Crea un refresh token nuevo para el usuario y lo devuelve."""
        ...

    async def obtener_por_hash(self, token_hash: str) -> RefreshTokenRegistro | None:
        """Busca un refresh token por su hash, esté vigente o revocado."""
        ...

    async def rotar(
        self,
        token_hash_actual: str,
        usuario_id: int,
        token_hash_nuevo: str,
        expires_at_nuevo: datetime,
    ) -> RefreshTokenRegistro | None:
        """Revoca `token_hash_actual` (si seguía vigente) y crea el reemplazo, en una única
        transacción.

        Devuelve `None` sin crear nada si `token_hash_actual` ya no estaba vigente al momento
        de revocarlo (carrera: otro request lo rotó o lo revocó primero). El caller debe tratar
        ese caso como un reuso de refresh token.
        """
        ...

    async def revocar_por_hash(self, token_hash: str) -> None:
        """Revoca el token si existe y sigue vigente. Idempotente: no falla si no existe."""
        ...

    async def revocar_todos_de_usuario(self, usuario_id: int) -> None:
        """Revoca todos los refresh tokens activos del usuario (detección de robo)."""
        ...


class DocumentoRepository(Protocol):
    """Acceso a los documentos, su archivo original y sus chunks (OCR + RAG)."""

    async def crear(
        self,
        nombre_archivo: str,
        tipo_contenido: str,
        tamano_bytes: int,
        idioma: str,
        creado_por_id: int,
        contenido: bytes,
        sha256: str,
        fuente_url: str | None = None,
    ) -> int:
        """Crea el documento (estado `pendiente`) y guarda su archivo original, en una única
        transacción. Devuelve el id creado.

        `fuente_url` es la url de origen cuando el documento se cargó desde una fuente externa
        (`cli cargar-corpus`); las cargas manuales por la API la dejan en `None`.
        """
        ...

    async def obtener(self, documento_id: int) -> DocumentoResponse | None:
        """Devuelve el documento por id, o `None` si no existe."""
        ...

    async def obtener_id_por_sha256(self, sha256: str) -> int | None:
        """Devuelve el id del documento cuyo archivo tiene ese `sha256`, o `None` si no existe.

        Lo usa `cli cargar-corpus` para no cargar dos veces el mismo contenido.
        """
        ...

    async def listar(self, limite: int, offset: int) -> tuple[list[DocumentoResponse], int]:
        """Lista los documentos paginados (más nuevo primero) y el total sin paginar."""
        ...

    async def obtener_ids_procesados(self, documento_ids: list[int]) -> set[int]:
        """De `documento_ids`, devuelve el subconjunto que existe y está en estado `procesado`."""
        ...

    async def obtener_para_procesar(self, documento_id: int) -> DocumentoParaProcesar | None:
        """Devuelve los datos que necesita el worker (idioma, tipo y contenido del archivo)."""
        ...

    async def marcar_procesando(self, documento_id: int) -> None:
        """Marca el documento como `procesando`."""
        ...

    async def marcar_error(self, documento_id: int, error_detalle: str) -> None:
        """Marca el documento como `error`, con un mensaje genérico en `error_detalle`."""
        ...

    async def guardar_resultado(
        self, documento_id: int, paginas: int, chunks: list[ChunkParaGuardar]
    ) -> None:
        """Reemplaza los chunks del documento por `chunks` y lo marca `procesado`, con
        `paginas` páginas, en una única transacción. Borra los chunks previos primero (el
        reprocesamiento es idempotente).
        """
        ...

    async def listar_ids_pendientes_o_procesando(self) -> list[int]:
        """Ids de documentos que quedaron sin terminar de procesar (para reencolar al arrancar)."""
        ...

    async def buscar_similares(
        self, embedding: list[float], top_k: int, documento_ids: list[int] | None
    ) -> list[ChunkSimilar]:
        """Busca los `top_k` chunks más similares a `embedding`, entre los documentos
        `procesado` (y, si se indica, solo entre `documento_ids`).
        """
        ...
