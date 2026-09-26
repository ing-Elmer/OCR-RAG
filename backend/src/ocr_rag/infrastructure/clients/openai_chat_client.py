"""Cliente de chat sobre la API de OpenAI, usado para responder preguntas del RAG."""

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

_PROMPT_SISTEMA = (
    "Sos un asistente que responde preguntas usando exclusivamente la información de los "
    "contextos numerados que te da el usuario. Citá la fuente de cada afirmación con su "
    "número entre corchetes (por ejemplo [1]). Si la información de los contextos no alcanza "
    "para responder la pregunta, decilo explícitamente en lugar de inventar una respuesta."
)

_TEMPERATURA_RESPUESTA = 0.1


class OpenAiChatClient:
    """Implementación de `ChatClient` (`core.clients`) usando el modelo de chat de OpenAI
    configurado en `Settings.openai_chat_model`.
    """

    def __init__(self, cliente: AsyncOpenAI, modelo: str) -> None:
        self._cliente = cliente
        self._modelo = modelo

    async def responder(self, pregunta: str, contextos: list[str]) -> str:
        """Genera una respuesta a `pregunta` usando solo la información de `contextos`."""
        mensaje_usuario = "\n\n".join([*contextos, f"Pregunta: {pregunta}"])
        mensajes: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=_PROMPT_SISTEMA),
            ChatCompletionUserMessageParam(role="user", content=mensaje_usuario),
        ]
        respuesta = await self._cliente.chat.completions.create(
            model=self._modelo,
            temperature=_TEMPERATURA_RESPUESTA,
            messages=mensajes,
        )
        contenido = respuesta.choices[0].message.content
        return contenido or ""
