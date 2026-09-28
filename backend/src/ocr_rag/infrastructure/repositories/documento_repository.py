"""Repositorio de documentos, su archivo original y sus chunks, sobre PostgreSQL/pgvector."""

from psycopg.rows import class_row

from ocr_rag.core.schemas.documento import (
    ChunkParaGuardar,
    ChunkSimilar,
    DocumentoParaProcesar,
    DocumentoResponse,
    TipoDocumento,
)
from ocr_rag.infrastructure.db import ConnectionFactory

_COLUMNAS_DOCUMENTO = """
    SELECT d.id,
           d.nombre_archivo,
           a.tipo_contenido,
           a.tamano_bytes,
           d.estado,
           d.idioma,
           d.paginas,
           COALESCE(c.cantidad, 0) AS cantidad_chunks,
           d.error_detalle,
           d.created_at,
           d.fuente_url,
           d.tipo_documento,
           d.norma
      FROM ocr_rag.ocr_documento d
      JOIN ocr_rag.ocr_documento_archivo a ON a.documento_id = d.id
      LEFT JOIN (
          SELECT documento_id, count(*) AS cantidad
            FROM ocr_rag.ocr_documento_chunk
           GROUP BY documento_id
      ) c ON c.documento_id = d.id
"""

_SQL_CREAR_DOCUMENTO = """
    INSERT INTO ocr_rag.ocr_documento
        (nombre_archivo, idioma, creado_por_id, fuente_url, tipo_documento, norma,
         clasificacion_pendiente)
    VALUES
        (%(nombre_archivo)s, %(idioma)s, %(creado_por_id)s, %(fuente_url)s, %(tipo_documento)s,
         %(norma)s, %(clasificacion_pendiente)s)
    RETURNING id
"""

_SQL_CREAR_ARCHIVO = """
    INSERT INTO ocr_rag.ocr_documento_archivo
        (documento_id, contenido, tipo_contenido, tamano_bytes, sha256)
    VALUES (%(documento_id)s, %(contenido)s, %(tipo_contenido)s, %(tamano_bytes)s, %(sha256)s)
"""

_SQL_OBTENER = _COLUMNAS_DOCUMENTO + " WHERE d.id = %(documento_id)s"

_SQL_LISTAR = (
    _COLUMNAS_DOCUMENTO
    + """
     ORDER BY d.created_at DESC
     LIMIT %(limite)s OFFSET %(offset)s
"""
)

_SQL_CONTAR = "SELECT count(*) FROM ocr_rag.ocr_documento"

_SQL_OBTENER_ID_POR_SHA256 = """
    SELECT documento_id
      FROM ocr_rag.ocr_documento_archivo
     WHERE sha256 = %(sha256)s
"""

_SQL_OBTENER_IDS_PROCESADOS = """
    SELECT id
      FROM ocr_rag.ocr_documento
     WHERE id = ANY(%(documento_ids)s)
       AND estado = 'procesado'
"""

_SQL_TOMAR_PARA_PROCESAR = """
    UPDATE ocr_rag.ocr_documento d
       SET estado = 'procesando', updated_at = now()
      FROM ocr_rag.ocr_documento_archivo a
     WHERE d.id = %(documento_id)s
       AND a.documento_id = d.id
       AND d.estado <> 'procesando'
    RETURNING d.id, d.idioma, a.tipo_contenido, a.contenido, d.tipo_documento, d.norma,
              d.version_procesamiento, d.clasificacion_pendiente
"""

_SQL_MARCAR_ERROR = """
    UPDATE ocr_rag.ocr_documento
       SET estado = 'error', error_detalle = %(error_detalle)s, updated_at = now()
     WHERE id = %(documento_id)s AND version_procesamiento = %(version_procesamiento)s
     RETURNING id
"""

_SQL_MARCAR_PROCESADO = """
    UPDATE ocr_rag.ocr_documento
       SET estado = 'procesado', paginas = %(paginas)s, error_detalle = NULL, updated_at = now()
     WHERE id = %(documento_id)s AND version_procesamiento = %(version_procesamiento)s
     RETURNING id
"""

_SQL_ACTUALIZAR_CLASIFICACION = """
    UPDATE ocr_rag.ocr_documento
       SET tipo_documento = %(tipo_documento)s, clasificacion_pendiente = false, updated_at = now()
     WHERE id = %(documento_id)s
       AND clasificacion_pendiente
       AND version_procesamiento = %(version_procesamiento)s
     RETURNING id
"""

_SQL_ACTUALIZAR = """
    UPDATE ocr_rag.ocr_documento
       SET tipo_documento = COALESCE(%(tipo_documento)s, tipo_documento),
           norma = CASE WHEN %(actualizar_norma)s THEN %(norma)s ELSE norma END,
           clasificacion_pendiente = CASE
               WHEN %(tipo_documento)s IS NOT NULL THEN false
               ELSE clasificacion_pendiente
           END,
           version_procesamiento = CASE
               WHEN %(reencolar)s THEN version_procesamiento + 1
               ELSE version_procesamiento
           END,
           estado = CASE WHEN %(reencolar)s THEN 'pendiente' ELSE estado END,
           updated_at = now()
     WHERE id = %(documento_id)s
     RETURNING id
"""

_SQL_INCREMENTAR_VERSION = """
    UPDATE ocr_rag.ocr_documento
       SET version_procesamiento = version_procesamiento + 1, updated_at = now()
     WHERE id = %(documento_id)s
"""

_SQL_RESETEAR_PROCESANDO_A_PENDIENTE = """
    UPDATE ocr_rag.ocr_documento
       SET estado = 'pendiente', updated_at = now()
     WHERE estado = 'procesando'
"""

_SQL_BORRAR_CHUNKS = "DELETE FROM ocr_rag.ocr_documento_chunk WHERE documento_id = %(documento_id)s"

_SQL_INSERTAR_CHUNK = """
    INSERT INTO ocr_rag.ocr_documento_chunk
        (documento_id, orden, contenido, pagina, embedding, articulo)
    VALUES
        (%(documento_id)s, %(orden)s, %(contenido)s, %(pagina)s, %(embedding)s::vector,
         %(articulo)s)
"""

_SQL_LISTAR_IDS_PENDIENTES = """
    SELECT id
      FROM ocr_rag.ocr_documento
     WHERE estado = 'pendiente'
     ORDER BY id
"""

_COLUMNAS_CHUNK_SIMILAR = """
    SELECT c.documento_id,
           d.nombre_archivo,
           c.orden,
           c.pagina,
           c.contenido,
           1 - (c.embedding <=> %(embedding)s::vector) AS similitud,
           d.fuente_url,
           d.norma,
           c.articulo,
           d.tipo_documento
      FROM ocr_rag.ocr_documento_chunk c
      JOIN ocr_rag.ocr_documento d ON d.id = c.documento_id
     WHERE d.estado = 'procesado'
       AND (
           %(documento_ids)s::bigint[] IS NULL
           OR c.documento_id = ANY(%(documento_ids)s::bigint[])
       )
       AND (
           %(tipos_documento)s::varchar[] IS NULL
           OR d.tipo_documento = ANY(%(tipos_documento)s::varchar[])
       )
"""

_SQL_BUSCAR_CANDIDATOS_VECTORIALES = (
    _COLUMNAS_CHUNK_SIMILAR
    + """
     ORDER BY c.embedding <=> %(embedding)s::vector
     LIMIT %(limite)s
"""
)

# OR rescata el Art. 94 del CAUCA IV aunque la pregunta incluya "requisitos":
# AND lo excluiría porque ese término no aparece en su definición de tránsito aduanero.
# Sin términos útiles, el cast de '' a tsquery es válido y @@ devuelve falso: cero filas.
_SQL_BUSCAR_CANDIDATOS_LEXICOS = (
    """
    WITH consulta AS MATERIALIZED (
        SELECT replace(plainto_tsquery('spanish', %(pregunta)s)::text, ' & ', ' | ')::tsquery AS q
    )
"""
    + _COLUMNAS_CHUNK_SIMILAR
    + """
       AND c.contenido_tsv @@ (SELECT q FROM consulta)
     ORDER BY ts_rank_cd(c.contenido_tsv, (SELECT q FROM consulta)) DESC
     LIMIT %(limite)s
"""
)


def _embedding_a_literal(embedding: list[float]) -> str:
    """Serializa un embedding como el literal de texto que espera `pgvector` (`'[x,y,...]'`)."""
    return "[" + ",".join(str(valor) for valor in embedding) + "]"


class PostgresDocumentoRepository:
    """Implementación de `DocumentoRepository` (`core.repositories`) sobre PostgreSQL."""

    def __init__(self, db: ConnectionFactory) -> None:
        self._db = db

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
        """
        async with self._db.connection("MAIN") as conn, conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    _SQL_CREAR_DOCUMENTO,
                    {
                        "nombre_archivo": nombre_archivo,
                        "idioma": idioma,
                        "creado_por_id": creado_por_id,
                        "fuente_url": fuente_url,
                        "tipo_documento": tipo_documento,
                        "norma": norma,
                        "clasificacion_pendiente": clasificacion_pendiente,
                    },
                )
                fila = await cur.fetchone()
            if fila is None:
                raise RuntimeError("El INSERT de ocr_documento no devolvió el id creado")
            documento_id: int = fila[0]

            async with conn.cursor() as cur:
                await cur.execute(
                    _SQL_CREAR_ARCHIVO,
                    {
                        "documento_id": documento_id,
                        "contenido": contenido,
                        "tipo_contenido": tipo_contenido,
                        "tamano_bytes": tamano_bytes,
                        "sha256": sha256,
                    },
                )
        return documento_id

    async def obtener(self, documento_id: int) -> DocumentoResponse | None:
        """Devuelve el documento por id, o `None` si no existe."""
        row_factory = class_row(DocumentoResponse)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(_SQL_OBTENER, {"documento_id": documento_id})
            return await cur.fetchone()

    async def listar(self, limite: int, offset: int) -> tuple[list[DocumentoResponse], int]:
        """Lista los documentos paginados (más nuevo primero) y el total sin paginar."""
        row_factory = class_row(DocumentoResponse)
        async with self._db.connection("MAIN") as conn:
            async with conn.cursor(row_factory=row_factory) as cur:
                await cur.execute(_SQL_LISTAR, {"limite": limite, "offset": offset})
                documentos = await cur.fetchall()
            async with conn.cursor() as cur:
                await cur.execute(_SQL_CONTAR)
                fila_total = await cur.fetchone()
        total = fila_total[0] if fila_total is not None else 0
        return documentos, total

    async def obtener_id_por_sha256(self, sha256: str) -> int | None:
        """Devuelve el id del documento cuyo archivo tiene ese `sha256`, o `None` si no existe."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_OBTENER_ID_POR_SHA256, {"sha256": sha256})
            fila = await cur.fetchone()
            return fila[0] if fila is not None else None

    async def obtener_ids_procesados(self, documento_ids: list[int]) -> set[int]:
        """De `documento_ids`, devuelve el subconjunto que existe y está en estado `procesado`."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_OBTENER_IDS_PROCESADOS, {"documento_ids": documento_ids})
            filas = await cur.fetchall()
            return {fila[0] for fila in filas}

    async def tomar_para_procesar(self, documento_id: int) -> DocumentoParaProcesar | None:
        """Toma `documento_id` en forma exclusiva para procesarlo: lo marca `procesando` y
        devuelve los datos que necesita el worker, en una única sentencia atómica.

        Devuelve `None` si el documento no existe o si ya estaba `procesando` (otro proceso lo
        tiene tomado).
        """
        row_factory = class_row(DocumentoParaProcesar)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(_SQL_TOMAR_PARA_PROCESAR, {"documento_id": documento_id})
            return await cur.fetchone()

    async def marcar_error(
        self, documento_id: int, error_detalle: str, version_procesamiento: int
    ) -> bool:
        """Marca el documento como `error`, con un mensaje genérico en `error_detalle`, solo si
        `version_procesamiento` sigue siendo la vigente. Devuelve si se aplicó.
        """
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(
                _SQL_MARCAR_ERROR,
                {
                    "documento_id": documento_id,
                    "error_detalle": error_detalle,
                    "version_procesamiento": version_procesamiento,
                },
            )
            fila = await cur.fetchone()
            return fila is not None

    async def guardar_resultado(
        self,
        documento_id: int,
        paginas: int,
        chunks: list[ChunkParaGuardar],
        version_procesamiento: int,
    ) -> bool:
        """Reemplaza los chunks del documento por `chunks` y lo marca `procesado`, con
        `paginas` páginas, en una única transacción, solo si `version_procesamiento` sigue
        siendo la vigente. Devuelve si se guardó.
        """
        async with self._db.connection("MAIN") as conn, conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    _SQL_MARCAR_PROCESADO,
                    {
                        "documento_id": documento_id,
                        "paginas": paginas,
                        "version_procesamiento": version_procesamiento,
                    },
                )
                fila = await cur.fetchone()
            if fila is None:
                return False

            async with conn.cursor() as cur:
                await cur.execute(_SQL_BORRAR_CHUNKS, {"documento_id": documento_id})
                if chunks:
                    parametros = [
                        {
                            "documento_id": documento_id,
                            "orden": chunk.orden,
                            "contenido": chunk.contenido,
                            "pagina": chunk.pagina,
                            "embedding": _embedding_a_literal(chunk.embedding),
                            "articulo": chunk.articulo,
                        }
                        for chunk in chunks
                    ]
                    await cur.executemany(_SQL_INSERTAR_CHUNK, parametros)
        return True

    async def actualizar_clasificacion(
        self, documento_id: int, tipo_documento: TipoDocumento, version_procesamiento: int
    ) -> bool:
        """Guarda el `tipo_documento` de la clasificación automática y limpia
        `clasificacion_pendiente`, solo si seguía pendiente y la versión sigue siendo la
        vigente. Devuelve si se aplicó.
        """
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(
                _SQL_ACTUALIZAR_CLASIFICACION,
                {
                    "documento_id": documento_id,
                    "tipo_documento": tipo_documento,
                    "version_procesamiento": version_procesamiento,
                },
            )
            fila = await cur.fetchone()
            return fila is not None

    async def actualizar(
        self,
        documento_id: int,
        tipo_documento: TipoDocumento | None,
        norma: str | None,
        *,
        actualizar_norma: bool,
        reencolar: bool,
    ) -> bool:
        """Actualiza `tipo_documento` (si no es `None`) y/o `norma` (si `actualizar_norma`) de
        `documento_id`; si `reencolar`, además incrementa `version_procesamiento` y pone
        `estado = 'pendiente'`. Devuelve si el documento existía.
        """
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(
                _SQL_ACTUALIZAR,
                {
                    "documento_id": documento_id,
                    "tipo_documento": tipo_documento,
                    "norma": norma,
                    "actualizar_norma": actualizar_norma,
                    "reencolar": reencolar,
                },
            )
            fila = await cur.fetchone()
            return fila is not None

    async def incrementar_version(self, documento_id: int) -> None:
        """Incrementa `version_procesamiento`, sin tocar el estado."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_INCREMENTAR_VERSION, {"documento_id": documento_id})

    async def resetear_procesando_a_pendiente(self) -> int:
        """Devuelve a `pendiente` todos los documentos que quedaron `procesando`. Devuelve la
        cantidad de documentos afectados.
        """
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_RESETEAR_PROCESANDO_A_PENDIENTE)
            return cur.rowcount

    async def listar_ids_pendientes(self) -> list[int]:
        """Ids de documentos `pendiente` (para reencolar su procesamiento al arrancar)."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_LISTAR_IDS_PENDIENTES)
            filas = await cur.fetchall()
            return [fila[0] for fila in filas]

    async def buscar_candidatos_vectoriales(
        self,
        embedding: list[float],
        limite: int,
        documento_ids: list[int] | None,
        tipos_documento: list[TipoDocumento] | None,
    ) -> list[ChunkSimilar]:
        """Busca los `limite` chunks más cercanos a `embedding` por similitud coseno, entre los
        documentos `procesado` (y, si se indica, solo entre `documento_ids` y/o
        `tipos_documento`).
        """
        row_factory = class_row(ChunkSimilar)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(
                _SQL_BUSCAR_CANDIDATOS_VECTORIALES,
                {
                    "embedding": _embedding_a_literal(embedding),
                    "documento_ids": documento_ids,
                    "tipos_documento": tipos_documento,
                    "limite": limite,
                },
            )
            return await cur.fetchall()

    async def buscar_candidatos_lexicos(
        self,
        pregunta: str,
        embedding: list[float],
        limite: int,
        documento_ids: list[int] | None,
        tipos_documento: list[TipoDocumento] | None,
    ) -> list[ChunkSimilar]:
        """Busca los `limite` chunks que contienen al menos un término útil de `pregunta`
        (`plainto_tsquery` con OR), ordenados por `ts_rank_cd`, entre documentos `procesado`
        (y, si se indica, solo entre `documento_ids` y/o `tipos_documento`). Sin términos útiles
        devuelve una lista vacía. `embedding` solo se usa para calcular la similitud coseno
        real de cada candidato, no para ordenar.
        """
        row_factory = class_row(ChunkSimilar)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(
                _SQL_BUSCAR_CANDIDATOS_LEXICOS,
                {
                    "pregunta": pregunta,
                    "embedding": _embedding_a_literal(embedding),
                    "documento_ids": documento_ids,
                    "tipos_documento": tipos_documento,
                    "limite": limite,
                },
            )
            return await cur.fetchall()
