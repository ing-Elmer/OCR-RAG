"""Validaciones de negocio sobre documentos: carga y existencia."""

import re

from ocr_rag.core.exceptions import NotFoundError, ValidationError
from ocr_rag.core.repositories import DocumentoRepository
from ocr_rag.core.schemas.documento import DocumentoResponse
from ocr_rag.core.settings import Settings

_EXTENSIONES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg", "tiff"}
_TIPOS_CONTENIDO_PERMITIDOS = {"application/pdf", "image/png", "image/jpeg", "image/tiff"}
_PATRON_IDIOMA = re.compile(r"^[a-z]{3}(\+[a-z]{3})*$")

_BYTES_POR_MB = 1024 * 1024


class DocumentoValidator:
    """Valida los datos de carga de un documento y su existencia."""

    def __init__(self, repositorio: DocumentoRepository, settings: Settings) -> None:
        self._repositorio = repositorio
        self._settings = settings

    def validar_carga(
        self,
        nombre_archivo: str,
        tipo_contenido: str,
        tamano_bytes: int,
        idioma: str | None,
    ) -> str:
        """Valida extensión, content-type, tamaño e idioma del archivo a cargar.

        Devuelve el idioma normalizado (el recibido, o `Settings.tesseract_langs` por defecto).
        Lanza `ValidationError` con los errores por campo (`archivo`, `idioma`) si algo falla.
        """
        errores: dict[str, list[str]] = {}

        extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        if extension not in _EXTENSIONES_PERMITIDAS:
            errores.setdefault("archivo", []).append("La extensión del archivo no está permitida")
        if tipo_contenido not in _TIPOS_CONTENIDO_PERMITIDOS:
            errores.setdefault("archivo", []).append("El tipo de archivo no está permitido")
        if tamano_bytes <= 0:
            errores.setdefault("archivo", []).append("El archivo está vacío")

        limite_bytes = self._settings.max_upload_mb * _BYTES_POR_MB
        if tamano_bytes > limite_bytes:
            errores.setdefault("archivo", []).append(
                f"El archivo supera el tamaño máximo permitido ({self._settings.max_upload_mb} MB)"
            )

        idioma_normalizado = idioma or self._settings.tesseract_langs
        if not _PATRON_IDIOMA.match(idioma_normalizado):
            errores.setdefault("idioma", []).append("El idioma no tiene un formato válido")

        if errores:
            raise ValidationError("Los datos del documento no son válidos", errores)

        return idioma_normalizado

    async def validar_existente(self, documento_id: int) -> DocumentoResponse:
        """Verifica que el documento exista; devuelve sus datos.

        Lanza `NotFoundError` si no existe.
        """
        documento = await self._repositorio.obtener(documento_id)
        if documento is None:
            raise NotFoundError(f"No se encontró el documento {documento_id}")
        return documento
