"""Modelo base para los DTOs de la API."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """DTO base que se serializa en camelCase pero acepta población por nombre de campo.

    Todos los DTOs de entrada y salida de la API heredan de esta clase para cumplir el
    contrato compartido con el frontend (JSON en camelCase).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
