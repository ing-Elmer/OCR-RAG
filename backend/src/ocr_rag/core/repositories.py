"""Interfaces (`Protocol`) de los repositorios: las implementa `infrastructure`."""

from datetime import datetime
from typing import Protocol

from ocr_rag.core.schemas.auth import RefreshTokenRegistro
from ocr_rag.core.schemas.documento import (
    ChunkParaGuardar,
    ChunkSimilar,
    DocumentoParaProcesar,
    DocumentoResponse,
    TipoDocumento,
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
        tipo_documento: TipoDocumento = "otro",
        norma: str | None = None,
        clasificacion_pendiente: bool = False,
    ) -> int:
        """Crea el documento (estado `pendiente`) y guarda su archivo original, en una única
        transacción. Devuelve el id creado.

        `fuente_url` es la url de origen cuando el documento se cargó desde una fuente externa
        (`cli cargar-corpus`); las cargas manuales por la API la dejan en `None`. `tipo_documento`
        es `"otro"` cuando la carga no indicó un tipo: el worker lo reemplaza por el que resulte
        de clasificar el documento, una vez extraído el texto. `clasificacion_pendiente` debe ser
        `True` en ese caso (la carga no indicó `tipoDocumento`), para que el worker sepa que debe
        clasificar aunque el proceso se reinicie antes de procesarlo.
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

    async def tomar_para_procesar(self, documento_id: int) -> DocumentoParaProcesar | None:
        """Toma `documento_id` en forma exclusiva para procesarlo: lo marca `procesando` (junto
        con los datos que necesita el worker) solo si no lo estaba ya, en una única sentencia
        atómica.

        Devuelve `None` si el documento no existe o si otro proceso ya lo tiene tomado (su
        `estado` ya era `procesando`); en ambos casos el caller no debe procesar nada. Reemplaza
        a los antiguos `obtener_para_procesar` + `marcar_procesando` (que dejaban una ventana
        entre leer y marcar donde dos procesos podían tomar el mismo documento a la vez).
        """
        ...

    async def marcar_error(
        self, documento_id: int, error_detalle: str, version_procesamiento: int
    ) -> bool:
        """Marca el documento como `error`, con un mensaje genérico en `error_detalle`, solo si
        `version_procesamiento` sigue siendo la vigente (la que devolvió `tomar_para_procesar`).

        Devuelve si se aplicó. Si la versión ya cambió (un reprocesamiento más nuevo se encoló
        mientras este corría), no toca el documento: ya hay un resultado más reciente en camino.
        """
        ...

    async def guardar_resultado(
        self,
        documento_id: int,
        paginas: int,
        chunks: list[ChunkParaGuardar],
        version_procesamiento: int,
    ) -> bool:
        """Reemplaza los chunks del documento por `chunks` y lo marca `procesado`, con
        `paginas` páginas, en una única transacción, solo si `version_procesamiento` sigue
        siendo la vigente (la que devolvió `tomar_para_procesar`).

        Devuelve si se guardó. Si la versión ya cambió mientras este procesamiento corría (un
        reprocesamiento más nuevo se encoló, por ejemplo por un PATCH que cambió el tipo), no
        toca los chunks existentes ni el estado: descarta este resultado, que ya quedó obsoleto.
        Borra los chunks previos antes de insertar los nuevos (el reprocesamiento es idempotente).
        """
        ...

    async def actualizar_clasificacion(
        self, documento_id: int, tipo_documento: TipoDocumento, version_procesamiento: int
    ) -> bool:
        """Guarda el `tipo_documento` resultante de la clasificación automática y limpia
        `clasificacion_pendiente`, solo si seguía pendiente y `version_procesamiento` sigue
        siendo la vigente.

        Devuelve si se aplicó. Si no (una edición manual del tipo llegó primero, o hay un
        reprocesamiento más nuevo en curso), el caller debe releer el tipo vigente del documento
        y usar ese para el chunking: la edición manual siempre gana sobre la clasificación
        automática.
        """
        ...

    async def actualizar(
        self,
        documento_id: int,
        tipo_documento: TipoDocumento | None,
        norma: str | None,
        *,
        actualizar_norma: bool,
        reencolar: bool,
    ) -> bool:
        """Actualiza `tipo_documento` (si no es `None`) y/o `norma` (si `actualizar_norma` es
        `True`; `norma=None` la limpia) de `documento_id`.

        Si `tipo_documento` no es `None`, también limpia `clasificacion_pendiente` (una edición
        manual del tipo gana siempre sobre la clasificación automática). Si `reencolar` es
        `True` (el caller ya determinó que `tipo_documento` cruza a o desde `"normativa"`),
        además incrementa `version_procesamiento` y pone `estado = 'pendiente'`, para que el
        reprocesamiento que encola el caller use la versión nueva.

        Devuelve si el documento existía. La usa `PATCH /api/documentos/{id}`.
        """
        ...

    async def incrementar_version(self, documento_id: int) -> None:
        """Incrementa `version_procesamiento`, sin tocar el estado.

        La usa `cli reprocesar` antes de tomar el documento, para descartar cualquier
        procesamiento en vuelo que todavía sostenga una versión anterior (aunque este documento
        siga `procesando` y la propia toma termine "omitida").
        """
        ...

    async def resetear_procesando_a_pendiente(self) -> int:
        """Devuelve a `pendiente` todos los documentos que quedaron `procesando`.

        Se usa al arrancar el proceso de la API: un reinicio (deploy, caída) corta el worker a
        mitad de un procesamiento y el documento queda `procesando` para siempre si nadie lo
        libera. Devuelve la cantidad de documentos afectados, para loguearla.
        """
        ...

    async def listar_ids_pendientes(self) -> list[int]:
        """Ids de documentos `pendiente` (para reencolar su procesamiento al arrancar)."""
        ...

    async def buscar_candidatos_vectoriales(
        self,
        embedding: list[float],
        limite: int,
        documento_ids: list[int] | None,
        tipos_documento: list[TipoDocumento] | None,
    ) -> list[ChunkSimilar]:
        """Busca los `limite` chunks más cercanos a `embedding` por similitud coseno (`<=>`),
        entre los documentos `procesado` (y, si se indica, solo entre `documento_ids` y/o
        `tipos_documento`). Es una de las dos listas de candidatos de la búsqueda híbrida; la
        fusión (RRF) la hace `application`.
        """
        ...

    async def buscar_candidatos_lexicos(
        self,
        pregunta: str,
        embedding: list[float],
        limite: int,
        documento_ids: list[int] | None,
        tipos_documento: list[TipoDocumento] | None,
    ) -> list[ChunkSimilar]:
        """Busca los `limite` chunks cuyo `contenido_tsv` matchea `pregunta` (búsqueda de texto
        completo, `websearch_to_tsquery`), ordenados por `ts_rank_cd`, entre los documentos
        `procesado` (y, si se indica, solo entre `documento_ids` y/o `tipos_documento`).

        `embedding` se usa solo para calcular la similitud coseno real de cada candidato (no
        para ordenar): así un chunk que entra por texto completo también trae una similitud
        comparable con la de `buscar_candidatos_vectoriales`.
        """
        ...
