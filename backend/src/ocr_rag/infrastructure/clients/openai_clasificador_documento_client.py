"""Cliente de clasificación automática de documentos sobre la API de OpenAI."""

import logging

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from ocr_rag.core.schemas.documento import TIPOS_DOCUMENTO, TipoDocumento

logger = logging.getLogger(__name__)

_TIPO_POR_DEFECTO: TipoDocumento = "otro"
_TEMPERATURA_CLASIFICACION = 0.0

_PROMPT_SISTEMA = (
    "Clasificá el documento que te pasa el usuario en exactamente una de estas categorías: "
    + ", ".join(TIPOS_DOCUMENTO)
    + ". Respondé únicamente con el nombre exacto de la categoría, en minúsculas y sin texto "
    "adicional."
)


class OpenAiClasificadorDocumentoClient:
    """Implementación de `ClasificadorDocumento` (`core.clients`) usando el modelo de chat de
    OpenAI configurado en `Settings.openai_chat_model`.

    Nunca lanza: ante cualquier excepción (incluido un timeout, ya configurado en el cliente de
    OpenAI compartido) o una respuesta que no sea exactamente uno de los valores de
    `TIPOS_DOCUMENTO`, resuelve a `"otro"` y deja un `logger.warning`, para que un problema de
    clasificación nunca interrumpa el procesamiento del documento.
    """

    def __init__(self, cliente: AsyncOpenAI, modelo: str) -> None:
        self._cliente = cliente
        self._modelo = modelo

    async def clasificar(self, texto: str) -> TipoDocumento:
        """Clasifica `texto` (una muestra del documento) en una de las categorías de
        `TipoDocumento`.
        """
        mensajes: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=_PROMPT_SISTEMA),
            ChatCompletionUserMessageParam(role="user", content=texto),
        ]
        try:
            respuesta = await self._cliente.chat.completions.create(
                model=self._modelo,
                temperature=_TEMPERATURA_CLASIFICACION,
                messages=mensajes,
            )
        except Exception:
            logger.warning(
                "Falló la clasificación automática del documento; se usa '%s'",
                _TIPO_POR_DEFECTO,
                exc_info=True,
            )
            return _TIPO_POR_DEFECTO

        contenido = (respuesta.choices[0].message.content or "").strip().lower()
        if contenido not in TIPOS_DOCUMENTO:
            logger.warning(
                "La clasificación automática devolvió un valor inesperado (%r); se usa '%s'",
                contenido,
                _TIPO_POR_DEFECTO,
            )
            return _TIPO_POR_DEFECTO
        return contenido
