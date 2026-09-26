"""Cliente de embeddings sobre la API de OpenAI."""

from openai import AsyncOpenAI


class OpenAiEmbeddingClient:
    """Implementación de `EmbeddingClient` (`core.clients`) usando el modelo de embeddings
    de OpenAI configurado en `Settings.openai_embedding_model`.
    """

    def __init__(self, cliente: AsyncOpenAI, modelo: str) -> None:
        self._cliente = cliente
        self._modelo = modelo

    async def generar_embedding(self, texto: str) -> list[float]:
        """Genera el vector de embedding del texto usando el modelo configurado."""
        respuesta = await self._cliente.embeddings.create(model=self._modelo, input=texto)
        return list(respuesta.data[0].embedding)
