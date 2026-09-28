"""Tests de `OpenAiChatClient`: arma los encabezados de cada fragmento y llama al chat de OpenAI
con un doble de prueba (no pega a la red).
"""

from types import SimpleNamespace
from typing import Any

from ocr_rag.core.schemas.documento import FragmentoContexto
from ocr_rag.infrastructure.clients.openai_chat_client import OpenAiChatClient


class _ClienteOpenAiFake:
    """Doble mínimo de `AsyncOpenAI`: solo expone `chat.completions.create` y guarda los
    argumentos con los que se lo llamó.
    """

    def __init__(self, respuesta: str = "Respuesta de prueba [1]") -> None:
        self.respuesta = respuesta
        self.llamadas: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.llamadas.append(kwargs)
        mensaje = SimpleNamespace(content=self.respuesta)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


async def test_responder_arma_el_encabezado_completo_con_norma_articulo_y_pagina() -> None:
    cliente_fake = _ClienteOpenAiFake()
    client = OpenAiChatClient(cliente_fake, "gpt-4o-mini")  # type: ignore[arg-type]
    fragmentos = [
        FragmentoContexto(
            numero=1,
            contenido="El tránsito aduanero es el régimen...",
            nombre_archivo="cauca_iv.pdf",
            norma="CAUCA IV",
            articulo="94",
            pagina=12,
        )
    ]

    await client.responder("¿Qué es el tránsito aduanero?", fragmentos)

    mensaje_usuario = cliente_fake.llamadas[0]["messages"][1]["content"]
    assert "[1] CAUCA IV, Art. 94 (pág. 12)" in mensaje_usuario
    assert "El tránsito aduanero es el régimen..." in mensaje_usuario


async def test_responder_omite_las_partes_del_encabezado_que_faltan() -> None:
    cliente_fake = _ClienteOpenAiFake()
    client = OpenAiChatClient(cliente_fake, "gpt-4o-mini")  # type: ignore[arg-type]
    fragmentos = [
        FragmentoContexto(
            numero=2, contenido="x", nombre_archivo="recauca.pdf", norma="RECAUCA IV"
        ),
        FragmentoContexto(numero=3, contenido="x", nombre_archivo="contrato.pdf"),
        FragmentoContexto(
            numero=4, contenido="x", nombre_archivo="a.pdf", norma="CAUCA IV", pagina=5
        ),
    ]

    await client.responder("pregunta", fragmentos)

    mensaje_usuario = cliente_fake.llamadas[0]["messages"][1]["content"]
    assert "[2] RECAUCA IV\nx" in mensaje_usuario
    assert "[3] contrato.pdf\nx" in mensaje_usuario
    assert "[4] CAUCA IV (pág. 5)\nx" in mensaje_usuario


async def test_responder_manda_los_encabezados_en_el_orden_de_las_fuentes() -> None:
    cliente_fake = _ClienteOpenAiFake()
    client = OpenAiChatClient(cliente_fake, "gpt-4o-mini")  # type: ignore[arg-type]
    fragmentos = [
        FragmentoContexto(numero=1, contenido="primero", nombre_archivo="a.pdf"),
        FragmentoContexto(numero=2, contenido="segundo", nombre_archivo="b.pdf"),
        FragmentoContexto(numero=3, contenido="tercero", nombre_archivo="c.pdf"),
    ]

    await client.responder("pregunta", fragmentos)

    mensaje_usuario = cliente_fake.llamadas[0]["messages"][1]["content"]
    assert mensaje_usuario.index("[1] a.pdf") < mensaje_usuario.index("[2] b.pdf")
    assert mensaje_usuario.index("[2] b.pdf") < mensaje_usuario.index("[3] c.pdf")


async def test_responder_manda_el_prompt_de_sistema_y_temperatura_baja() -> None:
    cliente_fake = _ClienteOpenAiFake()
    client = OpenAiChatClient(cliente_fake, "gpt-4o-mini")  # type: ignore[arg-type]

    await client.responder("pregunta", [])

    llamada = cliente_fake.llamadas[0]
    assert llamada["messages"][0]["role"] == "system"
    assert "CAUCA" in llamada["messages"][0]["content"]
    assert llamada["temperature"] <= 0.2


async def test_responder_devuelve_el_contenido_de_la_respuesta_del_modelo() -> None:
    cliente_fake = _ClienteOpenAiFake(respuesta="El tránsito aduanero es... [1]")
    client = OpenAiChatClient(cliente_fake, "gpt-4o-mini")  # type: ignore[arg-type]

    resultado = await client.responder("pregunta", [])

    assert resultado == "El tránsito aduanero es... [1]"
