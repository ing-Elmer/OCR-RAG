"""Fixtures compartidas para los tests del backend.

Las variables de entorno de acá abajo no son secretos: son valores ficticios para que
`Settings()` no falle al importar la app en los tests. Ningún test abre una conexión real
(los repositorios siempre se reemplazan con fakes vía `app.dependency_overrides`).
"""

import os

os.environ.setdefault("OCR_RAG_DB_MAIN_DSN", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OCR_RAG_JWT_SIGNING_KEY", "clave-de-test-no-usar-en-produccion")
os.environ.setdefault("OCR_RAG_JWT_ALGORITHM", "HS256")
os.environ.setdefault("OCR_RAG_OPENAI_API_KEY", "sk-test")
os.environ.setdefault("OCR_RAG_CORS_ORIGINS", "http://localhost:5173")

# ruff: noqa: E402 -- las variables de entorno deben fijarse antes de importar la app.

import datetime as dt
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from ocr_rag.api.dependencies import (
    get_auth_service,
    get_consulta_service,
    get_documento_service,
    get_health_service,
    get_usuario_service,
)
from ocr_rag.api.main import app
from ocr_rag.application.background import Tarea
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
from ocr_rag.core.exceptions import UnauthorizedError
from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.core.schemas.corpus import ArchivoDescargado
from ocr_rag.core.schemas.documento import (
    ChunkParaGuardar,
    ChunkSimilar,
    DocumentoParaProcesar,
    DocumentoResponse,
    EstadoDocumento,
    FragmentoContexto,
    PaginaExtraida,
    TipoDocumento,
)
from ocr_rag.core.schemas.usuario import CurrentUserResponse, UsuarioCredenciales
from ocr_rag.core.settings import get_settings


class FakeHealthRepository:
    """Implementación en memoria de `HealthRepository` (`core.repositories`), para tests."""

    def __init__(self, *, conexion_ok: bool = True) -> None:
        self.conexion_ok = conexion_ok

    async def verificar_conexion(self) -> bool:
        return self.conexion_ok


class FakeUsuarioRepository:
    """Implementación en memoria de `UsuarioRepository` (`core.repositories`), para tests."""

    def __init__(
        self,
        usuarios: dict[int, CurrentUserResponse] | None = None,
        credenciales: dict[str, UsuarioCredenciales] | None = None,
    ) -> None:
        self._usuarios = usuarios or {}
        self._credenciales = credenciales or {}
        self._usernames_existentes: set[str] = set(self._credenciales)

    async def obtener_usuario_actual(self, usuario_id: int) -> CurrentUserResponse | None:
        return self._usuarios.get(usuario_id)

    async def obtener_credenciales_activas(self, username: str) -> UsuarioCredenciales | None:
        return self._credenciales.get(username)

    async def existe_username(self, username: str) -> bool:
        return username in self._usernames_existentes

    async def crear(self, username: str, password_hash: str, nombre_completo: str) -> int:
        nuevo_id = max([*self._usuarios.keys(), 0]) + 1
        self._usernames_existentes.add(username)
        return nuevo_id

    async def asignar_rol(self, usuario_id: int, rol_codigo: str) -> None:
        return None

    def agregar(self, usuario: CurrentUserResponse) -> None:
        """Helper de test: agrega otro usuario (p. ej. sin permisos, para probar un 403)."""
        self._usuarios[usuario.id] = usuario


class FakeRefreshTokenRepository:
    """Implementación en memoria de `RefreshTokenRepository` (`core.repositories`), para tests."""

    def __init__(self, registros: dict[str, RefreshTokenRegistro] | None = None) -> None:
        self._registros = registros or {}
        self._siguiente_id = max([r.id for r in self._registros.values()], default=0) + 1

    async def crear(
        self, usuario_id: int, token_hash: str, expires_at: dt.datetime
    ) -> RefreshTokenRegistro:
        registro = RefreshTokenRegistro(
            id=self._siguiente_id,
            usuario_id=usuario_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )
        self._siguiente_id += 1
        self._registros[token_hash] = registro
        return registro

    async def obtener_por_hash(self, token_hash: str) -> RefreshTokenRegistro | None:
        return self._registros.get(token_hash)

    async def rotar(
        self,
        token_hash_actual: str,
        usuario_id: int,
        token_hash_nuevo: str,
        expires_at_nuevo: dt.datetime,
    ) -> RefreshTokenRegistro | None:
        """Revoca `token_hash_actual` solo si seguía vigente; si no, devuelve `None`.

        Simula el `UPDATE ... WHERE revoked_at IS NULL` condicional del repositorio real: si
        el token ya no existe o ya estaba revocado, no crea nada (carrera / reuso).
        """
        registro_actual = self._registros.get(token_hash_actual)
        if registro_actual is None or registro_actual.revoked_at is not None:
            return None
        await self.revocar_por_hash(token_hash_actual)
        return await self.crear(usuario_id, token_hash_nuevo, expires_at_nuevo)

    async def revocar_por_hash(self, token_hash: str) -> None:
        registro = self._registros.get(token_hash)
        if registro is not None and registro.revoked_at is None:
            self._registros[token_hash] = registro.model_copy(
                update={"revoked_at": dt.datetime.now(dt.UTC)}
            )

    async def revocar_todos_de_usuario(self, usuario_id: int) -> None:
        for token_hash, registro in list(self._registros.items()):
            if registro.usuario_id == usuario_id and registro.revoked_at is None:
                self._registros[token_hash] = registro.model_copy(
                    update={"revoked_at": dt.datetime.now(dt.UTC)}
                )

    def agregar(self, registro: RefreshTokenRegistro) -> None:
        """Helper de test: precarga un registro (p. ej. ya vencido o revocado)."""
        self._registros[registro.token_hash] = registro


class FakePasswordHasher:
    """Implementación en memoria de `PasswordHasher` (`core.security`), para tests.

    No usa bcrypt real: compara el password recibido contra el "hash" tal cual (se guarda con
    el prefijo `hash:`), para que los tests sean rápidos y determinísticos.
    """

    @staticmethod
    def hashear_para_test(password: str) -> str:
        return f"hash:{password}"

    async def hashear(self, password: str) -> str:
        return self.hashear_para_test(password)

    async def verificar(self, password: str, password_hash: str) -> bool:
        return password_hash == self.hashear_para_test(password)


class FakeTokenService:
    """Implementación en memoria de `TokenService` (`core.security`), para tests."""

    def crear_access_token(self, usuario_id: int) -> str:
        return f"access-token-de-{usuario_id}"

    def decodificar_access_token(self, token: str) -> int:
        prefijo = "access-token-de-"
        if not token.startswith(prefijo):
            raise UnauthorizedError("El token es inválido o expiró")
        return int(token.removeprefix(prefijo))


@dataclass
class _DocumentoAlmacenado:
    """Estado mutable de un documento fake, guardado en `FakeDocumentoRepository`."""

    nombre_archivo: str
    tipo_contenido: str
    tamano_bytes: int
    estado: EstadoDocumento
    idioma: str | None
    paginas: int | None
    error_detalle: str | None
    created_at: dt.datetime
    contenido: bytes
    sha256: str
    fuente_url: str | None = None
    tipo_documento: TipoDocumento = "otro"
    norma: str | None = None
    clasificacion_pendiente: bool = False
    version_procesamiento: int = 0


class FakeDocumentoRepository:
    """Implementación en memoria de `DocumentoRepository` (`core.repositories`), para tests."""

    def __init__(self) -> None:
        self._documentos: dict[int, _DocumentoAlmacenado] = {}
        self._chunks: dict[int, list[ChunkParaGuardar]] = {}
        self._siguiente_id = 1
        # Precargables desde el test: lo que deben devolver las dos búsquedas de candidatos.
        self.resultados_vectoriales: list[ChunkSimilar] = []
        self.resultados_lexicos: list[ChunkSimilar] = []

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
        tipo_documento: TipoDocumento = "otro",
        norma: str | None = None,
        clasificacion_pendiente: bool = False,
    ) -> int:
        documento_id = self._siguiente_id
        self._siguiente_id += 1
        self._documentos[documento_id] = _DocumentoAlmacenado(
            nombre_archivo=nombre_archivo,
            tipo_contenido=tipo_contenido,
            tamano_bytes=tamano_bytes,
            estado="pendiente",
            idioma=idioma,
            paginas=None,
            error_detalle=None,
            created_at=dt.datetime.now(dt.UTC),
            contenido=contenido,
            sha256=sha256,
            fuente_url=fuente_url,
            tipo_documento=tipo_documento,
            norma=norma,
            clasificacion_pendiente=clasificacion_pendiente,
        )
        self._chunks[documento_id] = []
        return documento_id

    async def obtener(self, documento_id: int) -> DocumentoResponse | None:
        datos = self._documentos.get(documento_id)
        if datos is None:
            return None
        return DocumentoResponse(
            id=documento_id,
            nombre_archivo=datos.nombre_archivo,
            tipo_contenido=datos.tipo_contenido,
            tamano_bytes=datos.tamano_bytes,
            estado=datos.estado,
            idioma=datos.idioma,
            paginas=datos.paginas,
            cantidad_chunks=len(self._chunks.get(documento_id, [])),
            error_detalle=datos.error_detalle,
            created_at=datos.created_at,
            fuente_url=datos.fuente_url,
            tipo_documento=datos.tipo_documento,
            norma=datos.norma,
        )

    async def obtener_id_por_sha256(self, sha256: str) -> int | None:
        for documento_id, datos in self._documentos.items():
            if datos.sha256 == sha256:
                return documento_id
        return None

    async def listar(self, limite: int, offset: int) -> tuple[list[DocumentoResponse], int]:
        ids_ordenados = sorted(
            self._documentos, key=lambda id_: self._documentos[id_].created_at, reverse=True
        )
        pagina_ids = ids_ordenados[offset : offset + limite]
        documentos: list[DocumentoResponse] = []
        for id_ in pagina_ids:
            documento = await self.obtener(id_)
            if documento is not None:
                documentos.append(documento)
        return documentos, len(ids_ordenados)

    async def obtener_ids_procesados(self, documento_ids: list[int]) -> set[int]:
        return {
            id_
            for id_ in documento_ids
            if id_ in self._documentos and self._documentos[id_].estado == "procesado"
        }

    async def tomar_para_procesar(self, documento_id: int) -> DocumentoParaProcesar | None:
        datos = self._documentos.get(documento_id)
        if datos is None or datos.estado == "procesando":
            return None
        datos.estado = "procesando"
        return DocumentoParaProcesar(
            id=documento_id,
            idioma=datos.idioma or "",
            tipo_contenido=datos.tipo_contenido,
            contenido=datos.contenido,
            tipo_documento=datos.tipo_documento,
            version_procesamiento=datos.version_procesamiento,
            clasificacion_pendiente=datos.clasificacion_pendiente,
            norma=datos.norma,
        )

    async def marcar_error(
        self, documento_id: int, error_detalle: str, version_procesamiento: int
    ) -> bool:
        datos = self._documentos.get(documento_id)
        if datos is None or datos.version_procesamiento != version_procesamiento:
            return False
        datos.estado = "error"
        datos.error_detalle = error_detalle
        return True

    async def guardar_resultado(
        self,
        documento_id: int,
        paginas: int,
        chunks: list[ChunkParaGuardar],
        version_procesamiento: int,
    ) -> bool:
        datos = self._documentos.get(documento_id)
        if datos is None or datos.version_procesamiento != version_procesamiento:
            return False
        self._chunks[documento_id] = list(chunks)
        datos.estado = "procesado"
        datos.paginas = paginas
        datos.error_detalle = None
        return True

    async def actualizar_clasificacion(
        self, documento_id: int, tipo_documento: TipoDocumento, version_procesamiento: int
    ) -> bool:
        datos = self._documentos.get(documento_id)
        if (
            datos is None
            or not datos.clasificacion_pendiente
            or datos.version_procesamiento != version_procesamiento
        ):
            return False
        datos.tipo_documento = tipo_documento
        datos.clasificacion_pendiente = False
        return True

    async def actualizar(
        self,
        documento_id: int,
        tipo_documento: TipoDocumento | None,
        norma: str | None,
        *,
        actualizar_norma: bool,
        reencolar: bool,
    ) -> bool:
        datos = self._documentos.get(documento_id)
        if datos is None:
            return False
        if tipo_documento is not None:
            datos.tipo_documento = tipo_documento
            datos.clasificacion_pendiente = False
        if actualizar_norma:
            datos.norma = norma
        if reencolar:
            datos.version_procesamiento += 1
            datos.estado = "pendiente"
        return True

    async def incrementar_version(self, documento_id: int) -> None:
        self._documentos[documento_id].version_procesamiento += 1

    async def resetear_procesando_a_pendiente(self) -> int:
        afectados = 0
        for datos in self._documentos.values():
            if datos.estado == "procesando":
                datos.estado = "pendiente"
                afectados += 1
        return afectados

    async def listar_ids_pendientes(self) -> list[int]:
        return [id_ for id_, datos in self._documentos.items() if datos.estado == "pendiente"]

    def version_de(self, documento_id: int) -> int:
        """Helper de test: `version_procesamiento` interna del documento."""
        return self._documentos[documento_id].version_procesamiento

    def clasificacion_pendiente_de(self, documento_id: int) -> bool:
        """Helper de test: `clasificacion_pendiente` interna del documento."""
        return self._documentos[documento_id].clasificacion_pendiente

    async def buscar_candidatos_vectoriales(
        self,
        embedding: list[float],
        limite: int,
        documento_ids: list[int] | None,
        tipos_documento: list[TipoDocumento] | None,
    ) -> list[ChunkSimilar]:
        return _filtrar_candidatos(
            self.resultados_vectoriales, limite, documento_ids, tipos_documento
        )

    async def buscar_candidatos_lexicos(
        self,
        pregunta: str,
        embedding: list[float],
        limite: int,
        documento_ids: list[int] | None,
        tipos_documento: list[TipoDocumento] | None,
    ) -> list[ChunkSimilar]:
        return _filtrar_candidatos(self.resultados_lexicos, limite, documento_ids, tipos_documento)

    def chunks_de(self, documento_id: int) -> list[ChunkParaGuardar]:
        """Helper de test: chunks guardados para `documento_id`."""
        return self._chunks.get(documento_id, [])


def _filtrar_candidatos(
    candidatos: list[ChunkSimilar],
    limite: int,
    documento_ids: list[int] | None,
    tipos_documento: list[TipoDocumento] | None,
) -> list[ChunkSimilar]:
    """Aplica a `candidatos` los mismos filtros que el repositorio real (documentos, tipos) y el
    límite de resultados, para las dos búsquedas fake de `FakeDocumentoRepository`.
    """
    resultados = candidatos
    if documento_ids is not None:
        resultados = [r for r in resultados if r.documento_id in documento_ids]
    if tipos_documento is not None:
        resultados = [r for r in resultados if r.tipo_documento in tipos_documento]
    return resultados[:limite]


class FakeOcrClient:
    """Implementación en memoria de `OcrClient` (`core.clients`), para tests."""

    def __init__(self, texto: str = "texto reconocido por ocr") -> None:
        self.texto = texto
        self.llamadas: list[tuple[bytes, str]] = []

    async def extraer_texto(self, contenido: bytes, idioma: str) -> str:
        self.llamadas.append((contenido, idioma))
        return self.texto


class FakeExtractorTexto:
    """Implementación en memoria de `ExtractorTexto` (`core.clients`), para tests."""

    def __init__(self, paginas: list[PaginaExtraida] | None = None) -> None:
        pagina_por_defecto = PaginaExtraida(numero=1, texto="Hola mundo. " * 20)
        self.paginas = paginas if paginas is not None else [pagina_por_defecto]
        self.llamadas: list[tuple[bytes, str, str]] = []

    async def extraer(
        self, contenido: bytes, tipo_contenido: str, idioma: str
    ) -> list[PaginaExtraida]:
        self.llamadas.append((contenido, tipo_contenido, idioma))
        return self.paginas


class FakeEmbeddingClient:
    """Implementación en memoria de `EmbeddingClient` (`core.clients`), para tests.

    Devuelve un vector determinístico por cada texto (según su largo), en el mismo orden.
    """

    def __init__(self, dimensiones: int = 3, *, falla: bool = False) -> None:
        self.dimensiones = dimensiones
        self.falla = falla
        self.lotes_recibidos: list[list[str]] = []

    async def generar_embeddings(self, textos: list[str]) -> list[list[float]]:
        self.lotes_recibidos.append(list(textos))
        if self.falla:
            raise RuntimeError("Falla simulada de la API de embeddings")
        return [[float(len(texto))] * self.dimensiones for texto in textos]


class FakeClasificadorDocumento:
    """Implementación en memoria de `ClasificadorDocumento` (`core.clients`), para tests.

    Por defecto devuelve `"otro"`, como haría la implementación real ante cualquier falla.
    """

    def __init__(self, tipo: TipoDocumento = "otro") -> None:
        self.tipo = tipo
        self.llamadas: list[str] = []

    async def clasificar(self, texto: str) -> TipoDocumento:
        self.llamadas.append(texto)
        return self.tipo


class FakeChatClient:
    """Implementación en memoria de `ChatClient` (`core.clients`), para tests."""

    def __init__(self, respuesta: str = "Respuesta de prueba [1]") -> None:
        self.respuesta = respuesta
        self.llamadas: list[tuple[str, list[FragmentoContexto]]] = []

    async def responder(self, pregunta: str, fragmentos: list[FragmentoContexto]) -> str:
        self.llamadas.append((pregunta, list(fragmentos)))
        return self.respuesta


class FakeDescargadorHttp:
    """Implementación en memoria de `DescargadorHttp` (`core.clients`), para tests.

    Por defecto, cualquier url devuelve un PDF mínimo válido. `respuestas` precarga un
    contenido específico por url; `fallos`, una excepción a lanzar en su lugar (simula una
    descarga inválida sin tocar la red).
    """

    def __init__(self) -> None:
        self.respuestas: dict[str, ArchivoDescargado] = {}
        self.fallos: dict[str, Exception] = {}
        self.urls_pedidas: list[str] = []

    async def descargar(self, url: str, limite_bytes: int) -> ArchivoDescargado:
        self.urls_pedidas.append(url)
        if url in self.fallos:
            raise self.fallos[url]
        if url in self.respuestas:
            return self.respuestas[url]
        return ArchivoDescargado(
            contenido=b"%PDF-1.4 contenido de prueba", tipo_contenido="application/pdf"
        )


class FakeBackgroundTaskQueue:
    """Implementación en memoria de `TaskEnqueuer` (`application.background`), para tests.

    No ejecuta las tareas encoladas: solo las guarda, para poder inspeccionarlas o correrlas a
    mano desde el test.
    """

    def __init__(self) -> None:
        self.tareas: list[Tarea] = []

    async def encolar(self, tarea: Tarea) -> None:
        self.tareas.append(tarea)


@pytest.fixture
def usuario_response() -> CurrentUserResponse:
    """Usuario de prueba con los permisos del catálogo, para ejercitar `require_permission`."""
    return CurrentUserResponse(
        id=1,
        username="ana",
        nombre_completo="Ana Pérez",
        roles=["ADMIN"],
        permisos=[
            "DOCUMENTO_VER",
            "DOCUMENTOS_VER",
            "DOCUMENTOS_CARGAR",
            "CONSULTAS_REALIZAR",
        ],
    )


# Contraseña "de verdad" del usuario de prueba `ana`, usada por los tests de login.
CONTRASENA_DE_PRUEBA = "clave-correcta-123"


@pytest.fixture
def fake_usuario_repository(usuario_response: CurrentUserResponse) -> FakeUsuarioRepository:
    """Repositorio fake precargado con `usuario_response` y sus credenciales de login."""
    credenciales = UsuarioCredenciales(
        id=usuario_response.id,
        username=usuario_response.username,
        password_hash=FakePasswordHasher.hashear_para_test(CONTRASENA_DE_PRUEBA),
    )
    return FakeUsuarioRepository(
        {usuario_response.id: usuario_response}, {credenciales.username: credenciales}
    )


@pytest.fixture
def fake_refresh_token_repository() -> FakeRefreshTokenRepository:
    """Repositorio fake de refresh tokens, vacío por defecto."""
    return FakeRefreshTokenRepository()


@pytest.fixture
def fake_documento_repository() -> FakeDocumentoRepository:
    """Repositorio fake de documentos, vacío por defecto."""
    return FakeDocumentoRepository()


@pytest.fixture
def fake_background_queue() -> FakeBackgroundTaskQueue:
    """Cola de tareas fake: captura las tareas encoladas sin ejecutarlas."""
    return FakeBackgroundTaskQueue()


@pytest_asyncio.fixture
async def async_client(
    fake_usuario_repository: FakeUsuarioRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_documento_repository: FakeDocumentoRepository,
    fake_background_queue: FakeBackgroundTaskQueue,
) -> AsyncIterator[AsyncClient]:
    """Cliente HTTP async contra la app, con los repositorios reemplazados por fakes."""
    app.dependency_overrides[get_health_service] = lambda: HealthService(FakeHealthRepository())
    app.dependency_overrides[get_usuario_service] = lambda: UsuarioService(
        fake_usuario_repository, UsuarioValidator(fake_usuario_repository)
    )
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        fake_refresh_token_repository,
        AuthValidator(fake_usuario_repository, fake_refresh_token_repository, FakePasswordHasher()),
        FakeTokenService(),
        get_settings(),
    )
    procesamiento_service = ProcesamientoDocumentoService(
        fake_documento_repository,
        FakeExtractorTexto(),
        FakeEmbeddingClient(),
        FakeClasificadorDocumento(),
    )
    app.dependency_overrides[get_documento_service] = lambda: DocumentoService(
        fake_documento_repository,
        DocumentoValidator(fake_documento_repository, get_settings()),
        procesamiento_service,
        fake_background_queue,
    )
    app.dependency_overrides[get_consulta_service] = lambda: ConsultaService(
        fake_documento_repository,
        ConsultaValidator(fake_documento_repository),
        FakeEmbeddingClient(),
        FakeChatClient(),
        get_settings(),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
