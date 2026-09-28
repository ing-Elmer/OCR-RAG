"""Cliente de chat sobre la API de OpenAI, usado para responder preguntas del RAG."""

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from ocr_rag.core.schemas.documento import FragmentoContexto

# Prompt de sistema: especialista en logística, comercio exterior y aduanas de Centroamérica.
# Reglas clave (ver Fase 1B): responder solo con los fragmentos, citar [n] + norma/artículo,
# distinguir CAUCA (Código) de RECAUCA (Reglamento), no forzar ítems sin respaldo, no exponer el
# funcionamiento interno ("el contexto"/"los fragmentos"), y avisar cuando la información no
# alcanza en vez de inventar.
_PROMPT_SISTEMA = (
    "Sos un especialista en logística, comercio exterior y aduanas de Centroamérica: dominás el "
    "CAUCA y el RECAUCA (Código y Reglamento Aduanero Uniforme Centroamericano), la DUCA, el "
    "Sistema Arancelario Centroamericano (SAC), los regímenes aduaneros, los Incoterms y los "
    "documentos de transporte internacional.\n\n"
    "Respondés preguntas usando exclusivamente la información de los fragmentos numerados que te "
    "da el usuario, cada uno con su norma y artículo cuando corresponde. Reglas:\n"
    "- Toda afirmación lleva su cita. Si el encabezado del fragmento trae artículo, la cita "
    "SIEMPRE nombra el artículo y la norma en el texto, seguidos del número entre corchetes: "
    '"Art. 94 del CAUCA IV [1]". Un "[1]" solo, sin el artículo, es una cita incompleta. Solo si '
    "el fragmento no trae artículo se cita con el número entre corchetes a secas.\n"
    "  Ejemplo de respuesta bien citada:\n"
    '  "El tránsito aduanero es el régimen por el cual las mercancías bajo control aduanero se '
    "transportan de una aduana a otra con suspensión de tributos (Art. 94 del CAUCA IV [1]). "
    "El plazo empieza a correr desde el registro de la autorización de salida del medio de "
    'transporte en la aduana de partida (Art. 395 del RECAUCA IV [2])."\n'
    "- El CAUCA es el Código (las normas sustantivas) y el RECAUCA es su Reglamento (el "
    "desarrollo operativo de esas normas): si ambos aplican a la pregunta, distinguilos "
    "explícitamente y explicá cómo se relacionan.\n"
    "- No fuerces en una lista ítems que no respondan a lo preguntado: si una parte de la "
    "pregunta no tiene respaldo en los fragmentos, decilo en lugar de completarla igual.\n"
    '- Nunca menciones "el contexto", "los fragmentos" ni cómo están armados internamente: '
    "hablale al usuario como si conocieras la normativa directamente, no como si estuvieras "
    "leyendo un documento que te pasaron.\n"
    "- Si la información no alcanza para responder (del todo o en parte), decilo explícitamente "
    "y sugerí qué norma o documento haría falta cargar para completar la respuesta.\n"
    "- Respondé en español técnico y claro, sin inventar artículos, normas ni datos que no estén "
    "en los fragmentos."
)

_TEMPERATURA_RESPUESTA = 0.1


class OpenAiChatClient:
    """Implementación de `ChatClient` (`core.clients`) usando el modelo de chat de OpenAI
    configurado en `Settings.openai_chat_model`.
    """

    def __init__(self, cliente: AsyncOpenAI, modelo: str) -> None:
        self._cliente = cliente
        self._modelo = modelo

    async def responder(self, pregunta: str, fragmentos: list[FragmentoContexto]) -> str:
        """Genera una respuesta a `pregunta` usando solo la información de `fragmentos`."""
        bloques_de_fragmento = [_armar_bloque(fragmento) for fragmento in fragmentos]
        mensaje_usuario = "\n\n".join([*bloques_de_fragmento, f"Pregunta: {pregunta}"])
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


def _armar_bloque(fragmento: FragmentoContexto) -> str:
    """Encabezado + contenido de un fragmento, tal como se le muestra al modelo."""
    return f"{_armar_encabezado(fragmento)}\n{fragmento.contenido}"


def _armar_encabezado(fragmento: FragmentoContexto) -> str:
    """`[n] <norma o nombre de archivo>, Art. <articulo> (pág. <p>)`, omitiendo lo que falte."""
    encabezado = f"[{fragmento.numero}] {fragmento.norma or fragmento.nombre_archivo}"
    if fragmento.articulo:
        encabezado += f", Art. {fragmento.articulo}"
    if fragmento.pagina is not None:
        encabezado += f" (pág. {fragmento.pagina})"
    return encabezado
