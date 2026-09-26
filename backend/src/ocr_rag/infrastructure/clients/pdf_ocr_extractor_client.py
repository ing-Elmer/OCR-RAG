"""Extractor de texto de documentos: PDF (texto nativo + OCR de páginas escaneadas) e imágenes.

`pypdfium2` (PDFium, el motor de Chrome) se usa tanto para leer el texto nativo como para
rasterizar. Se eligió sobre `pypdf` para el texto porque parte muchísimo menos las palabras: en
el RECAUCA IV de FAOLEX, pypdf dejó 566 palabras cortadas ("régi men") y pypdfium2, 32. Eso
degradaba los embeddings y la recuperación. Es bloqueante: corre en un threadpool.
"""

import io

import pypdfium2 as pdfium
from fastapi.concurrency import run_in_threadpool

from ocr_rag.core.clients import OcrClient
from ocr_rag.core.schemas.documento import PaginaExtraida

# Por debajo de este número de caracteres no blancos, la página se considera sin texto nativo
# útil y se rasteriza para pasarla por OCR.
_UMBRAL_CARACTERES_UTILES = 20

# ~300 dpi: pypdfium2 escala a partir de puntos PDF (72 por pulgada).
_DPI_RASTERIZADO = 300
_ESCALA_RASTERIZADO = _DPI_RASTERIZADO / 72

_TIPOS_IMAGEN = {"image/png", "image/jpeg", "image/tiff"}
_TIPO_PDF = "application/pdf"


class PdfOcrExtractorClient:
    """Implementación de `ExtractorTexto` (`core.clients`).

    Para PDF: extrae texto nativo por página con `pypdfium2`; si una página no tiene texto útil, la
    rasteriza con `pypdfium2` y la pasa por `OcrClient`. Para imágenes, usa `OcrClient` directo.
    """

    def __init__(self, ocr_client: OcrClient) -> None:
        self._ocr_client = ocr_client

    async def extraer(
        self, contenido: bytes, tipo_contenido: str, idioma: str
    ) -> list[PaginaExtraida]:
        """Devuelve el texto de cada página del documento, en orden."""
        if tipo_contenido == _TIPO_PDF:
            return await self._extraer_pdf(contenido, idioma)
        if tipo_contenido in _TIPOS_IMAGEN:
            texto = await self._ocr_client.extraer_texto(contenido, idioma)
            return [PaginaExtraida(numero=1, texto=texto)]
        raise ValueError(f"Tipo de contenido no soportado para extracción: {tipo_contenido}")

    async def _extraer_pdf(self, contenido: bytes, idioma: str) -> list[PaginaExtraida]:
        """Extrae el texto nativo de cada página; rasteriza y aplica OCR a las que no tengan."""
        textos_nativos = await run_in_threadpool(self._extraer_texto_nativo, contenido)
        paginas: list[PaginaExtraida] = []
        for indice, texto in enumerate(textos_nativos):
            numero = indice + 1
            if _tiene_texto_util(texto):
                paginas.append(PaginaExtraida(numero=numero, texto=texto))
                continue
            imagen_png = await run_in_threadpool(self._rasterizar_pagina, contenido, indice)
            texto_ocr = await self._ocr_client.extraer_texto(imagen_png, idioma)
            paginas.append(PaginaExtraida(numero=numero, texto=texto_ocr))
        return paginas

    @staticmethod
    def _extraer_texto_nativo(contenido: bytes) -> list[str]:
        """Nunca se llama directamente desde código async: es la parte bloqueante de `pypdfium2`.

        PDFium devuelve los saltos de línea como CRLF; se normalizan a LF para que el chunker
        los reconozca como límites de línea y párrafo.
        """
        documento = pdfium.PdfDocument(contenido)
        try:
            textos: list[str] = []
            for pagina in documento:
                try:
                    pagina_texto = pagina.get_textpage()
                    try:
                        texto = pagina_texto.get_text_range()
                    finally:
                        pagina_texto.close()
                finally:
                    pagina.close()
                textos.append(texto.replace("\r\n", "\n").replace("\r", "\n"))
            return textos
        finally:
            documento.close()

    @staticmethod
    def _rasterizar_pagina(contenido: bytes, indice_pagina: int) -> bytes:
        """Nunca se llama directamente desde código async: es la parte bloqueante de
        `pypdfium2`. Devuelve la página rasterizada como PNG.
        """
        documento = pdfium.PdfDocument(contenido)
        try:
            pagina = documento[indice_pagina]
            try:
                bitmap = pagina.render(scale=_ESCALA_RASTERIZADO)
                try:
                    imagen = bitmap.to_pil()
                    buffer = io.BytesIO()
                    imagen.save(buffer, format="PNG")
                    return buffer.getvalue()
                finally:
                    bitmap.close()
            finally:
                pagina.close()
        finally:
            documento.close()


def _tiene_texto_util(texto: str) -> bool:
    """Cuenta caracteres no blancos; por debajo del umbral, la página se considera sin texto."""
    caracteres_no_blancos = sum(1 for caracter in texto if not caracter.isspace())
    return caracteres_no_blancos >= _UMBRAL_CARACTERES_UTILES
