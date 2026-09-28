"""Métricas puras de evaluación del RAG: recuperación (¿aparece la fuente esperada?, en qué
posición) y citación (¿la respuesta menciona el artículo?), y su agregación (hit@k, MRR, % de
casos con todas las citas).

Sin I/O: reciben los datos ya resueltos por `ConsultaService` (fuentes, respuesta), así se
pueden testear sin red ni base real. Las usa `cli evaluar`.
"""

import re
from dataclasses import dataclass

from ocr_rag.core.schemas.documento import FuenteConsulta
from ocr_rag.core.schemas.evaluacion import ArticuloEsperado

# Frases que indican, en sustancia, que la respuesta no encontró información relevante (para
# evaluar el acierto de un caso negativo, con `esperados` vacío).
_PATRON_SIN_INFORMACION = re.compile(
    r"no\s+(se\s+)?(encontr|hall|dispon|teng[oa]|cuent[oa])", re.IGNORECASE
)


def _normalizar(texto: str) -> str:
    """Normaliza espacios y mayúsculas para comparar `norma`/`articulo` sin falsos negativos."""
    return " ".join(texto.strip().lower().split())


def _coincide(esperado: ArticuloEsperado, fuente: FuenteConsulta) -> bool:
    """Indica si `fuente` corresponde al mismo artículo que `esperado` (norma y artículo
    exactos, normalizando espacios y mayúsculas).
    """
    if fuente.norma is None or fuente.articulo is None:
        return False
    return _normalizar(fuente.norma) == _normalizar(esperado.norma) and _normalizar(
        fuente.articulo
    ) == _normalizar(esperado.articulo)


def posicion_recuperado(
    esperados: list[ArticuloEsperado], fuentes: list[FuenteConsulta]
) -> int | None:
    """Posición (1-based) de la primera fuente que coincide con algún esperado, o `None` si
    ninguna coincide.
    """
    for indice, fuente in enumerate(fuentes, start=1):
        if any(_coincide(esperado, fuente) for esperado in esperados):
            return indice
    return None


def respuesta_indica_sin_informacion(respuesta: str) -> bool:
    """Heurística: indica si `respuesta` dice, en sustancia, que no encontró información."""
    return _PATRON_SIN_INFORMACION.search(respuesta) is not None


def _patron_cita(articulo: str) -> re.Pattern[str]:
    """Regex tolerante para detectar la cita de `articulo` en una respuesta: "Art. 94",
    "Artículo 94", "art 94", con o sin punto y sin distinguir mayúsculas, sin confundirlo con un
    número más largo que lo contenga (p. ej. no matchea "94" dentro de "194").
    """
    numero = re.escape(articulo.strip())
    return re.compile(rf"\bart(?:\.|[íi]culo\.?)\s*{numero}\b", re.IGNORECASE)


def cita_articulo(articulo: str, respuesta: str) -> bool:
    """Indica si `respuesta` cita `articulo` (tolerante a las variantes de "artículo")."""
    return _patron_cita(articulo).search(respuesta) is not None


# Ventana de caracteres alrededor de una cita de artículo, usada como aproximación a "misma
# oración", para buscar cerca el nombre de la norma o una referencia de fuente `[n]`.
_VENTANA_ATRIBUCION_CARACTERES = 80

_PATRON_REFERENCIA_FUENTE = re.compile(r"\[(\d+)\]")


_PATRON_EDICION = re.compile(r"\s+(?P<edicion>[IVXLC]+)$", re.IGNORECASE)


def _patron_norma(norma: str) -> re.Pattern[str]:
    """Regex para detectar `norma` como token completo, no como substring: `\\b` evita que
    "CAUCA IV" matchee dentro de "RECAUCA IV" (no hay borde de palabra entre "RE" y "CAUCA").

    La edición en números romanos es opcional: la respuesta puede decir "Art. 52 del CAUCA"
    para una norma registrada como "CAUCA IV" (así cita un despachante; en la evaluación real el
    modelo lo escribe de esa forma casi siempre). El corpus tiene una sola edición vigente de
    cada norma, así que omitirla no genera ambigüedad.
    """
    norma_limpia = norma.strip()
    edicion = _PATRON_EDICION.search(norma_limpia)
    if edicion is None:
        return re.compile(rf"\b{re.escape(norma_limpia)}\b", re.IGNORECASE)
    base = norma_limpia[: edicion.start()]
    return re.compile(
        rf"\b{re.escape(base)}(?:\s+{re.escape(edicion.group('edicion'))})?\b", re.IGNORECASE
    )


def _norma_cerca_de_la_cita(norma: str, respuesta: str, inicio: int, fin: int) -> bool:
    """Indica si `norma` aparece dentro de una ventana de `_VENTANA_ATRIBUCION_CARACTERES`
    caracteres alrededor de la cita (posiciones `inicio`/`fin` en `respuesta`), como
    aproximación a "misma oración".
    """
    ventana_inicio = max(0, inicio - _VENTANA_ATRIBUCION_CARACTERES)
    ventana_fin = min(len(respuesta), fin + _VENTANA_ATRIBUCION_CARACTERES)
    return _patron_norma(norma).search(respuesta[ventana_inicio:ventana_fin]) is not None


def _fuente_referenciada_cerca(respuesta: str, fin: int) -> int | None:
    """Número (1-based) de la primera referencia `[n]` que sigue a una cita (dentro de la
    ventana de atribución), o `None` si no hay ninguna.
    """
    ventana_fin = min(len(respuesta), fin + _VENTANA_ATRIBUCION_CARACTERES)
    match = _PATRON_REFERENCIA_FUENTE.search(respuesta, fin, ventana_fin)
    return int(match.group(1)) if match else None


def cita_atribuible_a_norma(
    esperado: ArticuloEsperado, respuesta: str, fuentes: list[FuenteConsulta]
) -> bool:
    """Indica si `respuesta` cita el artículo de `esperado` de forma atribuible a su norma.

    No basta con que aparezca el número de artículo (eso lo confundiría, p. ej., "Art. 94 del
    RECAUCA IV" con "CAUCA IV" artículo 94): la cita debe poder atribuirse a la norma esperada,
    o bien porque el nombre de la norma aparece cerca (misma oración, aproximada por una ventana
    de caracteres), o bien porque lleva una referencia `[n]` cuya fuente (1-based en `fuentes`)
    es esa misma norma y artículo.
    """
    patron = _patron_cita(esperado.articulo)
    for match in patron.finditer(respuesta):
        if _norma_cerca_de_la_cita(esperado.norma, respuesta, match.start(), match.end()):
            return True
        numero_fuente = _fuente_referenciada_cerca(respuesta, match.end())
        if (
            numero_fuente is not None
            and 1 <= numero_fuente <= len(fuentes)
            and _coincide(esperado, fuentes[numero_fuente - 1])
        ):
            return True
    return False


def contar_citas(
    esperados: list[ArticuloEsperado], respuesta: str, fuentes: list[FuenteConsulta]
) -> tuple[int, int]:
    """Devuelve `(citas logradas, citas totales)`: cuántos de los `esperados` cita `respuesta`
    de forma atribuible a su norma (`cita_atribuible_a_norma`), sobre el total de `esperados`
    (0 de 0 en un caso negativo, que cuenta como completo).
    """
    total = len(esperados)
    logradas = sum(
        1 for esperado in esperados if cita_atribuible_a_norma(esperado, respuesta, fuentes)
    )
    return logradas, total


@dataclass(frozen=True, slots=True)
class ResultadoRecuperacion:
    """Resultado de evaluar la recuperación de un caso, positivo o negativo.

    En un caso negativo (`esperados` vacío), `posicion` es `1` si acertó (no hubo fuentes, o la
    respuesta dijo que no encontró información) y `None` si no, para que ese acierto sume el
    máximo posible a MRR sin necesitar una posición real.
    """

    acierto: bool
    posicion: int | None


def evaluar_recuperacion(
    esperados: list[ArticuloEsperado], fuentes: list[FuenteConsulta], respuesta: str
) -> ResultadoRecuperacion:
    """Evalúa si la recuperación de un caso fue correcta.

    Para un caso negativo (`esperados` vacío), acierta si no hay fuentes o la respuesta dice que
    no encontró información. Para uno positivo, acierta si alguna fuente coincide con algún
    esperado, y `posicion` es la del primer acierto.
    """
    if not esperados:
        acierto = not fuentes or respuesta_indica_sin_informacion(respuesta)
        return ResultadoRecuperacion(acierto=acierto, posicion=1 if acierto else None)
    posicion = posicion_recuperado(esperados, fuentes)
    return ResultadoRecuperacion(acierto=posicion is not None, posicion=posicion)


@dataclass(frozen=True, slots=True)
class ResumenEvaluacion:
    """Métricas agregadas de una corrida completa de evaluación."""

    hit_at_k: float
    mrr: float
    porcentaje_citas_completas: float


def calcular_resumen(
    recuperaciones: list[ResultadoRecuperacion], citas: list[tuple[int, int]]
) -> ResumenEvaluacion:
    """Agrega los resultados de todos los casos en hit@k, MRR y % de casos con todas las citas.

    `citas` trae, por caso y en el mismo orden que `recuperaciones`, el resultado de
    `contar_citas` (logradas, totales).
    """
    total = len(recuperaciones)
    if total == 0:
        return ResumenEvaluacion(hit_at_k=0.0, mrr=0.0, porcentaje_citas_completas=0.0)

    hit_at_k = sum(1 for resultado in recuperaciones if resultado.acierto) / total
    mrr = sum(1 / resultado.posicion for resultado in recuperaciones if resultado.posicion) / total
    citas_completas = sum(1 for logradas, totales in citas if logradas == totales)
    return ResumenEvaluacion(
        hit_at_k=hit_at_k, mrr=mrr, porcentaje_citas_completas=citas_completas / total
    )
