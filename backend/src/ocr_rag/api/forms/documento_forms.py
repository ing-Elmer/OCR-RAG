"""Modelo de formulario multipart de `POST /api/documentos`."""

from fastapi import File, Form, UploadFile

from ocr_rag.core.schemas.documento import TipoDocumento


class DocumentoCargaForm:
    """Campos multipart de la carga de un documento.

    `idioma` es opcional: si no se envía, el service lo completa con
    `Settings.tesseract_langs`. `tipoDocumento` también es opcional: si no se envía, el worker
    lo clasifica automáticamente después de extraer el texto.
    """

    def __init__(
        self,
        archivo: UploadFile = File(...),
        idioma: str | None = Form(None),
        tipo_documento: TipoDocumento | None = Form(None, alias="tipoDocumento"),
    ) -> None:
        self.archivo = archivo
        self.idioma = idioma
        self.tipo_documento = tipo_documento
