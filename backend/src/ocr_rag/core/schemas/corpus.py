"""DTOs del manifiesto de carga masiva del corpus normativo.

Uso interno del comando `cli cargar-corpus`: el manifiesto es un archivo TOML que nunca se sirve
por la API, así que estos modelos no heredan `CamelModel`. Las validaciones de forma (id, url,
idioma) siguen el mismo criterio que los DTOs de la API: se resuelven acá, con
`Field`/validators de Pydantic, antes de cualquier lógica de negocio.
"""

import re
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ocr_rag.core.schemas.documento import TipoDocumento

_PATRON_ID = re.compile(r"^[a-z0-9-]+$")
_PATRON_IDIOMA = re.compile(r"^[a-z]{3}(\+[a-z]{3})*$")


class FuenteCorpus(BaseModel):
    """Una fuente normativa del manifiesto de corpus: metadatos y url de descarga."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    titulo: str = Field(min_length=1)
    url: str
    idioma: str | None = None
    descripcion: str = ""
    licencia: str = ""
    verificado: date
    tipo: TipoDocumento = "normativa"
    norma: str | None = None

    @field_validator("id")
    @classmethod
    def _validar_id(cls, valor: str) -> str:
        if not _PATRON_ID.match(valor):
            raise ValueError("El id debe usar solo minúsculas, dígitos y guiones ([a-z0-9-]+)")
        return valor

    @field_validator("url")
    @classmethod
    def _validar_url(cls, valor: str) -> str:
        if not valor.startswith("https://"):
            raise ValueError("La url debe empezar con 'https://'")
        return valor

    @field_validator("idioma")
    @classmethod
    def _validar_idioma(cls, valor: str | None) -> str | None:
        if valor is not None and not _PATRON_IDIOMA.match(valor):
            raise ValueError("El idioma no tiene un formato válido (p. ej. 'spa' o 'spa+eng')")
        return valor


class ManifiestoCorpus(BaseModel):
    """Manifiesto completo de carga masiva: la lista de fuentes a cargar."""

    model_config = ConfigDict(frozen=True)

    fuente: list[FuenteCorpus] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validar_ids_unicos(self) -> "ManifiestoCorpus":
        ids = [fuente.id for fuente in self.fuente]
        duplicados = sorted({id_ for id_ in ids if ids.count(id_) > 1})
        if duplicados:
            raise ValueError(f"Ids de fuente duplicados en el manifiesto: {', '.join(duplicados)}")
        return self


@dataclass(frozen=True, slots=True)
class ArchivoDescargado:
    """Contenido descargado de una fuente, ya validado como PDF (uso interno del pipeline)."""

    contenido: bytes
    tipo_contenido: str | None
