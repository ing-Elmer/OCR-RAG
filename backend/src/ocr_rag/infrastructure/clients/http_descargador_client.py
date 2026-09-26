"""Descarga de archivos remotos por HTTPS, con límites de seguridad.

Uso interno del comando de CLI `cargar-corpus`: nunca se invoca desde un endpoint HTTP.
`urllib` es bloqueante, así que la descarga corre en un hilo aparte (`asyncio.to_thread`).
"""

import asyncio
import urllib.error
import urllib.request
from collections.abc import Callable
from contextlib import AbstractContextManager
from http.client import HTTPMessage
from typing import IO, Protocol

from ocr_rag.core.exceptions import DescargaInvalidaError
from ocr_rag.core.schemas.corpus import ArchivoDescargado

_USER_AGENT = "ocr-rag-cargar-corpus/1.0 (+https://github.com/ing-Elmer/OCR-RAG)"
_TIMEOUT_SEGUNDOS = 60
_TAMANO_LOTE_LECTURA = 64 * 1024
_FIRMA_PDF = b"%PDF-"
_TIPO_CONTENIDO_PDF = "application/pdf"


class _RespuestaHttp(Protocol):
    """Lo mínimo que necesita `UrllibDescargadorHttp` de una respuesta HTTP.

    Coincide estructuralmente con `http.client.HTTPResponse` (la respuesta real) y con el
    objeto que inyectan los tests, sin acoplar el tipo a `http.client`.
    """

    headers: HTTPMessage

    def read(self, tamano: int) -> bytes:
        """Lee hasta `tamano` bytes del cuerpo de la respuesta."""
        ...


class _RedirectorSoloHttps(urllib.request.HTTPRedirectHandler):
    """Rechaza cualquier redirección que no apunte a una url https."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        if not newurl.lower().startswith("https://"):
            raise DescargaInvalidaError(f"La descarga redirige a una url que no es https: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class UrllibDescargadorHttp:
    """Implementación de `DescargadorHttp` (`core.clients`) con la librería estándar `urllib`.

    `abrir` es inyectable (por defecto, un `OpenerDirector` de `urllib` con redirecciones
    limitadas a https): los tests lo reemplazan por un doble en memoria para no depender de la
    red.
    """

    def __init__(
        self,
        abrir: Callable[[urllib.request.Request], AbstractContextManager[_RespuestaHttp]]
        | None = None,
    ) -> None:
        self._abrir = abrir or self._abrir_con_urllib

    async def descargar(self, url: str, limite_bytes: int) -> ArchivoDescargado:
        """Descarga `url` en un hilo aparte (`urllib` es bloqueante)."""
        return await asyncio.to_thread(self._descargar_sync, url, limite_bytes)

    def _descargar_sync(self, url: str, limite_bytes: int) -> ArchivoDescargado:
        if not url.lower().startswith("https://"):
            raise DescargaInvalidaError(f"La url no usa https: {url}")

        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with self._abrir(request) as respuesta:
                return self._leer_respuesta(respuesta, limite_bytes)
        except OSError as error:
            raise DescargaInvalidaError(f"No se pudo descargar el archivo: {error}") from error

    def _abrir_con_urllib(
        self, request: urllib.request.Request
    ) -> AbstractContextManager[_RespuestaHttp]:
        opener = urllib.request.build_opener(_RedirectorSoloHttps())
        return opener.open(request, timeout=_TIMEOUT_SEGUNDOS)  # type: ignore[no-any-return]

    @staticmethod
    def _leer_respuesta(respuesta: _RespuestaHttp, limite_bytes: int) -> ArchivoDescargado:
        tipo_contenido = respuesta.headers.get_content_type()
        bloques: list[bytes] = []
        total = 0
        while True:
            bloque = respuesta.read(_TAMANO_LOTE_LECTURA)
            if not bloque:
                break
            total += len(bloque)
            if total > limite_bytes:
                raise DescargaInvalidaError(
                    f"El archivo supera el tamaño máximo permitido ({limite_bytes} bytes)"
                )
            bloques.append(bloque)

        contenido = b"".join(bloques)
        es_pdf = tipo_contenido == _TIPO_CONTENIDO_PDF or contenido.startswith(_FIRMA_PDF)
        if not es_pdf:
            raise DescargaInvalidaError(
                "El contenido descargado no parece ser un PDF "
                "(ni el content-type ni la firma del archivo coinciden)"
            )
        return ArchivoDescargado(contenido=contenido, tipo_contenido=tipo_contenido)
