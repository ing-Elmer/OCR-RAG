"""Cliente de OCR sobre Tesseract local, vía `pytesseract`."""

import io

import pytesseract
from fastapi.concurrency import run_in_threadpool
from PIL import Image


class TesseractOcrClient:
    """Implementación de `OcrClient` (`core.clients`) usando Tesseract instalado localmente.

    `pytesseract` es bloqueante: la extracción real corre en un threadpool para no bloquear
    el loop de eventos.
    """

    async def extraer_texto(self, contenido: bytes, idioma: str) -> str:
        """Reconoce el texto de una imagen (PNG/JPEG/TIFF) en el idioma indicado."""
        return await run_in_threadpool(self._extraer_texto_sync, contenido, idioma)

    @staticmethod
    def _extraer_texto_sync(contenido: bytes, idioma: str) -> str:
        """Ejecuta el reconocimiento. Nunca se llama directamente desde código async."""
        with Image.open(io.BytesIO(contenido)) as imagen:
            texto: str = pytesseract.image_to_string(imagen, lang=idioma)
        return texto
