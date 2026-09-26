"""Modelo de formulario multipart de `POST /api/documentos`."""

from fastapi import File, Form, UploadFile


class DocumentoCargaForm:
    """Campos multipart de la carga de un documento.

    `idioma` es opcional: si no se envía, el service lo completa con
    `Settings.tesseract_langs`.
    """

    def __init__(
        self,
        archivo: UploadFile = File(...),
        idioma: str | None = Form(None),
    ) -> None:
        self.archivo = archivo
        self.idioma = idioma
