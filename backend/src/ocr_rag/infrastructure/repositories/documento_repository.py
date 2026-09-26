"""Repositorio de documentos, su archivo original y sus chunks, sobre PostgreSQL/pgvector."""

from psycopg.rows import class_row

from ocr_rag.core.schemas.documento import (
    ChunkParaGuardar,
    ChunkSimilar,
    DocumentoParaProcesar,
    DocumentoResponse,
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
           d.fuente_url
      FROM ocr_rag.ocr_documento d
      JOIN ocr_rag.ocr_documento_archivo a ON a.documento_id = d.id
      LEFT JOIN (
          SELECT documento_id, count(*) AS cantidad
            FROM ocr_rag.ocr_documento_chunk
           GROUP BY documento_id
      ) c ON c.documento_id = d.id
"""

_SQL_CREAR_DOCUMENTO = """
    INSERT INTO ocr_rag.ocr_documento (nombre_archivo, idioma, creado_por_id, fuente_url)
    VALUES (%(nombre_archivo)s, %(idioma)s, %(creado_por_id)s, %(fuente_url)s)
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

_SQL_OBTENER_PARA_PROCESAR = """
    SELECT d.id, d.idioma, a.tipo_contenido, a.contenido
      FROM ocr_rag.ocr_documento d
      JOIN ocr_rag.ocr_documento_archivo a ON a.documento_id = d.id
     WHERE d.id = %(documento_id)s
"""

_SQL_MARCAR_PROCESANDO = """
    UPDATE ocr_rag.ocr_documento
       SET estado = 'procesando', updated_at = now()
     WHERE id = %(documento_id)s
"""

_SQL_MARCAR_ERROR = """
    UPDATE ocr_rag.ocr_documento
       SET estado = 'error', error_detalle = %(error_detalle)s, updated_at = now()
     WHERE id = %(documento_id)s
"""

_SQL_MARCAR_PROCESADO = """
    UPDATE ocr_rag.ocr_documento
       SET estado = 'procesado', paginas = %(paginas)s, error_detalle = NULL, updated_at = now()
     WHERE id = %(documento_id)s
"""

_SQL_BORRAR_CHUNKS = "DELETE FROM ocr_rag.ocr_documento_chunk WHERE documento_id = %(documento_id)s"

_SQL_INSERTAR_CHUNK = """
    INSERT INTO ocr_rag.ocr_documento_chunk (documento_id, orden, contenido, pagina, embedding)
    VALUES (%(documento_id)s, %(orden)s, %(contenido)s, %(pagina)s, %(embedding)s::vector)
"""

_SQL_LISTAR_IDS_PENDIENTES_O_PROCESANDO = """
    SELECT id
      FROM ocr_rag.ocr_documento
     WHERE estado IN ('pendiente', 'procesando')
     ORDER BY id
"""

_SQL_BUSCAR_SIMILARES = """
    SELECT c.documento_id,
           d.nombre_archivo,
           c.orden,
           c.pagina,
           c.contenido,
           1 - (c.embedding <=> %(embedding)s::vector) AS similitud,
           d.fuente_url
      FROM ocr_rag.ocr_documento_chunk c
      JOIN ocr_rag.ocr_documento d ON d.id = c.documento_id
     WHERE d.estado = 'procesado'
       AND (
           %(documento_ids)s::bigint[] IS NULL
           OR c.documento_id = ANY(%(documento_ids)s::bigint[])
       )
     ORDER BY c.embedding <=> %(embedding)s::vector
     LIMIT %(top_k)s
"""


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

    async def obtener_para_procesar(self, documento_id: int) -> DocumentoParaProcesar | None:
        """Devuelve los datos que necesita el worker (idioma, tipo y contenido del archivo)."""
        row_factory = class_row(DocumentoParaProcesar)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(_SQL_OBTENER_PARA_PROCESAR, {"documento_id": documento_id})
            return await cur.fetchone()

    async def marcar_procesando(self, documento_id: int) -> None:
        """Marca el documento como `procesando`."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_MARCAR_PROCESANDO, {"documento_id": documento_id})

    async def marcar_error(self, documento_id: int, error_detalle: str) -> None:
        """Marca el documento como `error`, con un mensaje genérico en `error_detalle`."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(
                _SQL_MARCAR_ERROR,
                {"documento_id": documento_id, "error_detalle": error_detalle},
            )

    async def guardar_resultado(
        self, documento_id: int, paginas: int, chunks: list[ChunkParaGuardar]
    ) -> None:
        """Reemplaza los chunks del documento por `chunks` y lo marca `procesado`, con
        `paginas` páginas, en una única transacción.
        """
        async with self._db.connection("MAIN") as conn, conn.transaction():
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
                        }
                        for chunk in chunks
                    ]
                    await cur.executemany(_SQL_INSERTAR_CHUNK, parametros)
            async with conn.cursor() as cur:
                await cur.execute(
                    _SQL_MARCAR_PROCESADO, {"documento_id": documento_id, "paginas": paginas}
                )

    async def listar_ids_pendientes_o_procesando(self) -> list[int]:
        """Ids de documentos que quedaron sin terminar de procesar (para reencolar al arrancar)."""
        async with self._db.connection("MAIN") as conn, conn.cursor() as cur:
            await cur.execute(_SQL_LISTAR_IDS_PENDIENTES_O_PROCESANDO)
            filas = await cur.fetchall()
            return [fila[0] for fila in filas]

    async def buscar_similares(
        self, embedding: list[float], top_k: int, documento_ids: list[int] | None
    ) -> list[ChunkSimilar]:
        """Busca los `top_k` chunks más similares a `embedding`, entre los documentos
        `procesado` (y, si se indica, solo entre `documento_ids`).
        """
        row_factory = class_row(ChunkSimilar)
        async with (
            self._db.connection("MAIN") as conn,
            conn.cursor(row_factory=row_factory) as cur,
        ):
            await cur.execute(
                _SQL_BUSCAR_SIMILARES,
                {
                    "embedding": _embedding_a_literal(embedding),
                    "documento_ids": documento_ids,
                    "top_k": top_k,
                },
            )
            return await cur.fetchall()
