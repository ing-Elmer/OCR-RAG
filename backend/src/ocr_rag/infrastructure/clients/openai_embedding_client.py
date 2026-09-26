"""Cliente de embeddings sobre la API de OpenAI."""

from openai import AsyncOpenAI


class OpenAiEmbeddingClient:
    """Implementación de `EmbeddingClient` (`core.clients`) usando el modelo de embeddings
    de OpenAI configurado en `Settings.openai_embedding_model`.
    """

    def __init__(self, cliente: AsyncOpenAI, modelo: str) -> None:
        self._cliente = cliente
        self._modelo = modelo

    async def generar_embeddings(self, textos: list[str]) -> list[list[float]]:
        """Genera, en una sola llamada, el vector de embedding de cada texto de `textos`.

        Conserva el orden de `textos` aunque la API no garantice devolverlos en ese orden.
        """
        if not textos:
            return []
        respuesta = await self._cliente.embeddings.create(model=self._modelo, input=textos)
        datos_ordenados = sorted(respuesta.data, key=lambda dato: dato.index)
        return [list(dato.embedding) for dato in datos_ordenados]
