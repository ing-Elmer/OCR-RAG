"""Comando `reprocesar`: repite el pipeline de OCR + chunking + embeddings sobre documentos ya
cargados, en el mismo proceso (sin encolar en background).

Reutiliza `ProcesamientoDocumentoService.procesar`, que ya borra los chunks previos del
documento en una única transacción antes de guardar los nuevos, así que reprocesar es idempotente.
Usa la misma toma exclusiva que el worker en background (vía `DocumentoService.reprocesar_ahora`,
que además incrementa `version_procesamiento` antes de tomar el documento, para descartar
cualquier procesamiento en vuelo que sostuviera una versión anterior): si el worker de la API
tiene el documento tomado, este comando lo informa como "omitido (en proceso)" en lugar de
tratarlo como un error. No fuerza una reclasificación: solo clasifica si `clasificacion_pendiente`
seguía en `True` en la base (por ejemplo, una carga sin tipo cuyo primer intento falló antes de
llegar a clasificar); si ya se clasificó o se editó manualmente, conserva ese tipo. Hace falta
para regenerar el corpus con un chunking nuevo.

Arma sus propias dependencias, igual que `cargar_corpus.py`: no hay un proceso ASGI que las
arme por él.
"""

import argparse
import asyncio
import sys

from openai import AsyncOpenAI

from ocr_rag.application.background import BackgroundTaskQueue
from ocr_rag.application.services.documento_service import DocumentoService
from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.application.validators.documento_validator import DocumentoValidator
from ocr_rag.core.exceptions import NotFoundError
from ocr_rag.core.schemas.documento import DocumentoResponse
from ocr_rag.core.settings import get_settings
from ocr_rag.infrastructure.clients.openai_clasificador_documento_client import (
    OpenAiClasificadorDocumentoClient,
)
from ocr_rag.infrastructure.clients.openai_embedding_client import OpenAiEmbeddingClient
from ocr_rag.infrastructure.clients.pdf_ocr_extractor_client import PdfOcrExtractorClient
from ocr_rag.infrastructure.clients.tesseract_ocr_client import TesseractOcrClient
from ocr_rag.infrastructure.db import ConnectionFactory
from ocr_rag.infrastructure.repositories.documento_repository import PostgresDocumentoRepository

# Timeout explícito para las llamadas a OpenAI (embeddings), igual que en `cargar_corpus.py`.
_TIMEOUT_OPENAI_SEGUNDOS = 60.0

# Estados que `--todos` omite, para no pisar el procesamiento del worker en background.
_ESTADOS_OMITIDOS_EN_TODOS = frozenset({"pendiente", "procesando"})

# Tamaño de página al recorrer el listado completo de documentos para resolver `--todos`.
_TAMANO_PAGINA_LISTADO = 200


def _parsear_argumentos(argv: list[str]) -> argparse.Namespace:
    """Define y parsea los argumentos del comando `reprocesar`."""
    parser = argparse.ArgumentParser(
        prog="python -m ocr_rag.cli reprocesar",
        description=(
            "Vuelve a extraer texto, limpiar encabezados, chunkear y generar embeddings de "
            "documentos ya cargados, en el mismo proceso (sin encolar). Antes de tomar cada "
            "documento incrementa su version_procesamiento, para descartar cualquier "
            "procesamiento en vuelo con una versión anterior; si el worker de la API lo tiene "
            "tomado en ese momento, lo informa como 'omitido (en proceso)' sin contarlo como "
            "error. Solo reclasifica si la clasificación automática seguía pendiente en la "
            "base; si no, conserva el tipoDocumento vigente. Un fallo en un documento no "
            "detiene a los demás."
        ),
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--todos",
        action="store_true",
        help="Reprocesa todos los documentos que no estén 'pendiente' ni 'procesando' (para no "
        "pisar al worker en background).",
    )
    grupo.add_argument(
        "--id",
        default=None,
        metavar="N[,N...]",
        help="Ids de documento a reprocesar, separados por coma (por ejemplo '7' o '3,7,12').",
    )
    return parser.parse_args(argv)


def parsear_ids(valor: str) -> list[int] | None:
    """Convierte `--id` en una lista de enteros, en el orden recibido.

    Devuelve `None` (e imprime el error) si algún valor no es un entero, o si no queda ningún id
    tras descartar los vacíos.
    """
    ids: list[int] = []
    for parte in valor.split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            ids.append(int(parte))
        except ValueError:
            print(f"Error: '{parte}' no es un id de documento válido")
            return None
    if not ids:
        print("Error: --id no tiene ningún id válido")
        return None
    return ids


async def resolver_documentos_todos(
    documento_service: DocumentoService,
) -> list[DocumentoResponse]:
    """Recorre el listado paginado completo y devuelve los documentos que no están 'pendiente'
    ni 'procesando', para no pisar al worker en background.
    """
    documentos: list[DocumentoResponse] = []
    offset = 0
    while True:
        pagina, total = await documento_service.listar(_TAMANO_PAGINA_LISTADO, offset)
        if not pagina:
            break
        documentos.extend(pagina)
        offset += len(pagina)
        if offset >= total:
            break
    return [
        documento for documento in documentos if documento.estado not in _ESTADOS_OMITIDOS_EN_TODOS
    ]


async def resolver_documentos_por_id(
    documento_service: DocumentoService, ids: list[int]
) -> list[DocumentoResponse] | None:
    """Busca cada id de `ids`, en el orden recibido.

    Devuelve `None` (e imprime el error) si alguno no existe.
    """
    documentos: list[DocumentoResponse] = []
    for documento_id in ids:
        try:
            documentos.append(await documento_service.obtener(documento_id))
        except NotFoundError:
            print(f"Error: no existe el documento {documento_id}")
            return None
    return documentos


async def ejecutar_reprocesamiento(
    documentos: list[DocumentoResponse], documento_service: DocumentoService
) -> int:
    """Reprocesa cada documento, imprime el progreso y el resumen final, y devuelve el exit code.

    Un fallo en un documento no detiene a los demás (`ProcesamientoDocumentoService.procesar`
    nunca propaga: deja el documento en estado `error`). Un documento que el worker de la API ya
    tiene tomado se informa como "omitido (en proceso)" y no cuenta como error. Exit 0 si ninguno
    terminó en `error`, 1 si al menos uno falló.
    """
    total = len(documentos)
    con_error = 0
    omitidos = 0
    for indice, documento in enumerate(documentos, start=1):
        print(
            f"[{indice}/{total}] #{documento.id} {documento.nombre_archivo} … reprocesando",
            flush=True,
        )
        tomado = await documento_service.reprocesar_ahora(documento.id)
        if not tomado:
            omitidos += 1
            print("    Omitido: en proceso (ya lo tiene tomado otro proceso)")
            continue
        resultado = await documento_service.obtener(documento.id)
        if resultado.estado == "error":
            con_error += 1
            print(f"    Error: {resultado.error_detalle}")
        else:
            print(f"    OK: {resultado.cantidad_chunks} chunks")

    reprocesados = total - con_error - omitidos
    print(
        f"Resumen: {reprocesados} reprocesados, {con_error} con error, {omitidos} omitidos "
        f"(de {total})."
    )
    return 1 if con_error else 0


async def _reprocesar(argv: list[str]) -> int:
    """Arma las dependencias contra la base de `Settings` y ejecuta el reprocesamiento."""
    args = _parsear_argumentos(argv)

    settings = get_settings()
    connection_factory = ConnectionFactory()
    await connection_factory.abrir("MAIN", settings.db_main_dsn.get_secret_value())
    openai_client = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(), timeout=_TIMEOUT_OPENAI_SEGUNDOS
    )
    try:
        documento_repositorio = PostgresDocumentoRepository(connection_factory)
        validador = DocumentoValidator(documento_repositorio, settings)
        procesador = ProcesamientoDocumentoService(
            documento_repositorio,
            PdfOcrExtractorClient(TesseractOcrClient()),
            OpenAiEmbeddingClient(openai_client, settings.openai_embedding_model),
            # `reprocesar` nunca clasifica automáticamente, pero el constructor del worker lo
            # exige igual.
            OpenAiClasificadorDocumentoClient(openai_client, settings.openai_chat_model),
        )
        # `BackgroundTaskQueue` sin `iniciar()`: el CLI no tiene worker, así que `procesar_ahora`
        # nunca la usa; la exige el constructor de `DocumentoService`.
        documento_service = DocumentoService(
            documento_repositorio, validador, procesador, BackgroundTaskQueue()
        )

        if args.todos:
            documentos = await resolver_documentos_todos(documento_service)
        else:
            ids = parsear_ids(args.id)
            if ids is None:
                return 1
            documentos_o_error = await resolver_documentos_por_id(documento_service, ids)
            if documentos_o_error is None:
                return 1
            documentos = documentos_o_error

        if not documentos:
            print("No hay documentos para reprocesar.")
            return 0

        return await ejecutar_reprocesamiento(documentos, documento_service)
    finally:
        await connection_factory.cerrar_todos()


def main() -> None:
    """Punto de entrada síncrono del comando.

    En Windows, `psycopg` async requiere un `SelectorEventLoop`: el `ProactorEventLoop` (el
    default) no soporta los sockets que usa `psycopg_pool`.
    """
    codigo = asyncio.run(_reprocesar(sys.argv[2:]), loop_factory=asyncio.SelectorEventLoop)
    raise SystemExit(codigo)
