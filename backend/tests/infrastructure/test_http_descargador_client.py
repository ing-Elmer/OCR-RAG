"""Tests de `UrllibDescargadorHttp` y de `_RedirectorSoloHttps`, sin tocar la red.

El `abrir` (equivalente a un `OpenerDirector.open`) es inyectable: los tests lo reemplazan por
un doble en memoria que expone un objeto con `.headers` (un `http.client.HTTPMessage`) y
`.read(tamano)`, tal como lo necesita `UrllibDescargadorHttp`.
"""

import io
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from http.client import HTTPMessage
from typing import NoReturn

import pytest

from ocr_rag.core.exceptions import DescargaInvalidaError
from ocr_rag.infrastructure.clients.http_descargador_client import (
    UrllibDescargadorHttp,
    _RedirectorSoloHttps,
)

_LIMITE_BYTES = 1024 * 1024


class _RespuestaFalsa:
    """Doble de `http.client.HTTPResponse`: solo lo que usa `UrllibDescargadorHttp`."""

    def __init__(self, contenido: bytes, tipo_contenido: str | None) -> None:
        self._restante = contenido
        self.headers = HTTPMessage()
        if tipo_contenido is not None:
            self.headers["Content-Type"] = tipo_contenido

    def read(self, tamano: int) -> bytes:
        bloque, self._restante = self._restante[:tamano], self._restante[tamano:]
        return bloque


@contextmanager
def _abrir_con(respuesta: _RespuestaFalsa) -> Iterator[_RespuestaFalsa]:
    yield respuesta


async def test_descargar_pdf_valido_por_content_type_devuelve_el_contenido() -> None:
    contenido = b"contenido binario de un pdf de prueba"
    respuesta = _RespuestaFalsa(contenido, "application/pdf")
    descargador = UrllibDescargadorHttp(abrir=lambda _req: _abrir_con(respuesta))

    archivo = await descargador.descargar("https://example.org/norma.pdf", _LIMITE_BYTES)

    assert archivo.contenido == contenido
    assert archivo.tipo_contenido == "application/pdf"


async def test_descargar_pdf_valido_por_firma_aunque_el_content_type_sea_generico() -> None:
    contenido = b"%PDF-1.4 contenido de prueba"
    respuesta = _RespuestaFalsa(contenido, "application/octet-stream")
    descargador = UrllibDescargadorHttp(abrir=lambda _req: _abrir_con(respuesta))

    archivo = await descargador.descargar("https://example.org/norma.pdf", _LIMITE_BYTES)

    assert archivo.contenido == contenido


async def test_descargar_url_http_lanza_error_sin_intentar_abrir_la_conexion() -> None:
    def _abrir_no_deberia_llamarse(_req: urllib.request.Request) -> NoReturn:
        raise AssertionError("no debería intentar abrir una conexión para una url http")

    descargador = UrllibDescargadorHttp(abrir=_abrir_no_deberia_llamarse)

    with pytest.raises(DescargaInvalidaError, match="https"):
        await descargador.descargar("http://example.org/norma.pdf", _LIMITE_BYTES)


async def test_descargar_contenido_que_no_es_pdf_lanza_error() -> None:
    respuesta = _RespuestaFalsa(b"<html>no es un pdf</html>", "text/html")
    descargador = UrllibDescargadorHttp(abrir=lambda _req: _abrir_con(respuesta))

    with pytest.raises(DescargaInvalidaError, match="PDF"):
        await descargador.descargar("https://example.org/pagina.html", _LIMITE_BYTES)


async def test_descargar_que_supera_el_limite_de_bytes_lanza_error() -> None:
    contenido = b"%PDF-1.4" + b"x" * 100
    respuesta = _RespuestaFalsa(contenido, "application/pdf")
    descargador = UrllibDescargadorHttp(abrir=lambda _req: _abrir_con(respuesta))

    with pytest.raises(DescargaInvalidaError, match="tamaño"):
        await descargador.descargar("https://example.org/norma.pdf", limite_bytes=10)


def test_redirector_solo_https_rechaza_redireccion_a_http() -> None:
    handler = _RedirectorSoloHttps()
    req = urllib.request.Request("https://example.org/norma.pdf")

    with pytest.raises(DescargaInvalidaError, match="https"):
        handler.redirect_request(
            req, io.BytesIO(), 302, "Found", HTTPMessage(), "http://example.org/otra.pdf"
        )


def test_redirector_solo_https_permite_redireccion_a_https() -> None:
    handler = _RedirectorSoloHttps()
    req = urllib.request.Request("https://example.org/norma.pdf")

    nuevo_request = handler.redirect_request(
        req, io.BytesIO(), 302, "Found", HTTPMessage(), "https://example.org/otra.pdf"
    )

    assert nuevo_request is not None
    assert nuevo_request.full_url == "https://example.org/otra.pdf"
