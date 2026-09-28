"""DTOs del dataset de evaluación del RAG (`cli evaluar`).

Uso interno del comando `cli evaluar`: el dataset es un archivo TOML que nunca se sirve por la
API, así que estos modelos no heredan `CamelModel`, igual criterio que `core/schemas/corpus.py`.
Las validaciones de forma (campos obligatorios, ids únicos) se resuelven acá, con
`Field`/validators de Pydantic, antes de cualquier lógica de negocio.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ArticuloEsperado(BaseModel):
    """Un artículo de una norma que una buena respuesta debería recuperar y citar."""

    model_config = ConfigDict(frozen=True)

    norma: str = Field(min_length=1)
    articulo: str = Field(min_length=1)


class CasoEvaluacion(BaseModel):
    """Un caso del dataset de evaluación: una pregunta y los artículos esperados.

    `esperados` puede ser una lista vacía: es un caso negativo, donde la respuesta correcta es
    que no hay información relevante en el corpus.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    pregunta: str = Field(min_length=1)
    esperados: list[ArticuloEsperado] = Field(default_factory=list)
    nota: str = ""


class DatasetEvaluacion(BaseModel):
    """Dataset completo de evaluación: la lista de casos."""

    model_config = ConfigDict(frozen=True)

    caso: list[CasoEvaluacion] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validar_ids_unicos(self) -> "DatasetEvaluacion":
        ids = [caso.id for caso in self.caso]
        duplicados = sorted({id_ for id_ in ids if ids.count(id_) > 1})
        if duplicados:
            raise ValueError(f"Ids de caso duplicados en el dataset: {', '.join(duplicados)}")
        return self
