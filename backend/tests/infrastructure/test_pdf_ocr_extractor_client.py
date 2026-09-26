"""Tests de `PdfOcrExtractorClient`, con un PDF generado en el test (`pypdf`)."""

import io

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from ocr_rag.infrastructure.clients.pdf_ocr_extractor_client import PdfOcrExtractorClient
from tests.conftest import FakeOcrClient


def _crear_pagina_con_texto(writer: PdfWriter, texto: str) -> None:
    """Agrega a `writer` una página con `texto` dibujado, usando un content stream a mano
    (no hay una API de alto nivel en `pypdf` para escribir texto: solo puede leerlo).
    """
    pagina = writer.add_blank_page(width=200, height=200)
    fuente = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    fuente_ref = writer._add_object(fuente)  # noqa: SLF001 -- única forma de armar el recurso
    fuentes = DictionaryObject({NameObject("/F1"): fuente_ref})
    recursos = DictionaryObject({NameObject("/Font"): fuentes})
    pagina[NameObject("/Resources")] = recursos

    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 24 Tf 10 100 Td ({texto}) Tj ET".encode("latin-1"))
    stream_ref = writer._add_object(stream)  # noqa: SLF001 -- ídem
    pagina[NameObject("/Contents")] = stream_ref


def _crear_pdf(*, texto_pagina_1: str, con_pagina_en_blanco: bool) -> bytes:
    writer = PdfWriter()
    _crear_pagina_con_texto(writer, texto_pagina_1)
    if con_pagina_en_blanco:
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


_TEXTO_NATIVO_PAGINA_1 = "Hola mundo, este es el texto nativo de la primera pagina."


async def test_extraer_pdf_con_texto_nativo_en_todas_las_paginas_no_usa_ocr() -> None:
    pdf = _crear_pdf(texto_pagina_1=_TEXTO_NATIVO_PAGINA_1, con_pagina_en_blanco=False)
    ocr_client = FakeOcrClient()
    extractor = PdfOcrExtractorClient(ocr_client)

    paginas = await extractor.extraer(pdf, "application/pdf", "spa")

    assert len(paginas) == 1
    assert paginas[0].numero == 1
    assert "Hola mundo" in paginas[0].texto
    assert ocr_client.llamadas == []


async def test_extraer_pdf_con_pagina_sin_texto_la_rasteriza_y_usa_ocr() -> None:
    pdf = _crear_pdf(texto_pagina_1=_TEXTO_NATIVO_PAGINA_1, con_pagina_en_blanco=True)
    ocr_client = FakeOcrClient(texto="texto reconocido por tesseract")
    extractor = PdfOcrExtractorClient(ocr_client)

    paginas = await extractor.extraer(pdf, "application/pdf", "spa")

    assert len(paginas) == 2
    assert "Hola mundo" in paginas[0].texto
    assert paginas[1].numero == 2
    assert paginas[1].texto == "texto reconocido por tesseract"
    # Se usó OCR solo para la segunda página (la que no tenía texto nativo útil).
    assert len(ocr_client.llamadas) == 1
    _, idioma_usado = ocr_client.llamadas[0]
    assert idioma_usado == "spa"


async def test_extraer_imagen_usa_ocr_directo_y_devuelve_una_sola_pagina() -> None:
    ocr_client = FakeOcrClient(texto="texto de la imagen")
    extractor = PdfOcrExtractorClient(ocr_client)

    paginas = await extractor.extraer(b"contenido-de-imagen", "image/png", "eng")

    assert len(paginas) == 1
    assert paginas[0].numero == 1
    assert paginas[0].texto == "texto de la imagen"
    assert ocr_client.llamadas == [(b"contenido-de-imagen", "eng")]


async def test_extraer_tipo_de_contenido_no_soportado_lanza_value_error() -> None:
    extractor = PdfOcrExtractorClient(FakeOcrClient())

    with pytest.raises(ValueError, match="no soportado"):
        await extractor.extraer(b"contenido", "application/zip", "spa")
