"""Limpieza de encabezados y pies de página repetidos: función pura, sin I/O.

Se aplica a las páginas extraídas antes del chunking: los documentos escaneados suelen traer el
mismo encabezado/pie en cada página (nombre de la norma, numeración) mezclado con el texto, y
eso degrada el chunking y la recuperación semántica.
"""

import re

from ocr_rag.application.chunking import PATRON_ARTICULO
from ocr_rag.core.schemas.documento import PaginaExtraida

# Por debajo de esta cantidad de páginas no hay señal suficiente para detectar repeticiones de
# forma confiable: solo se elimina la numeración de página.
_MINIMO_PAGINAS_PARA_LIMPIAR = 4

# Solo se consideran márgenes las primeras y últimas tres líneas no vacías de cada página.
_LINEAS_POR_MARGEN = 3

# Fracción mínima de páginas en las que debe repetirse una línea (normalizada) para
# considerarla encabezado/pie y descartarla.
_FRACCION_MINIMA_DE_REPETICION = 0.5

# Numeración de página: "Página 130 de 215", "12 de 215", "12 / 215", "Pág. 12", "- 12 -".
_PATRON_NUMERACION_PAGINA = re.compile(
    r"^\s*(?:p[aá]g(?:ina)?\.?\s*)?\d+\s*(?:de|/)\s*\d+\s*$"
    r"|^\s*p[aá]g(?:ina)?\.?\s*\d+\s*$"
    r"|^\s*-\s*\d+\s*-\s*$",
    re.IGNORECASE,
)

_PATRON_DIGITOS = re.compile(r"\d+")
_PATRON_ESPACIOS = re.compile(r"\s+")

# También se conservan rótulos aislados sin terminador. Esta protección es más conservadora
# que el chunking: no convierte esos rótulos en límites de artículo.
_PATRON_ARTICULO_SIN_TERMINADOR = re.compile(
    r"^[ \t]*(?:Art[íi]culo|Art\.)[ \t]+\d+(?:[ \t]*(?:bis|ter|quater))?[ \t]*$",
    re.IGNORECASE,
)


def limpiar_encabezados_pies(paginas: list[PaginaExtraida]) -> list[PaginaExtraida]:
    """Quita de `paginas` las líneas que son encabezado o pie de página.

    Con al menos cuatro páginas, detecta y elimina repeticiones solo en las primeras y últimas
    tres líneas no vacías. Normaliza dígitos y espacios y exige aparición en al menos la mitad
    de las páginas. Los encabezados de artículo se conservan siempre, incluso sin terminador.
    Elimina la numeración de página en cualquier posición y con cualquier cantidad de páginas.
    """
    lineas_repetidas = _detectar_lineas_repetidas(paginas)
    resultado: list[PaginaExtraida] = []
    for pagina in paginas:
        lineas = pagina.texto.split("\n")
        margenes = _indices_de_margenes(lineas)
        resultado.append(
            PaginaExtraida(
                numero=pagina.numero,
                texto="\n".join(
                    linea
                    for indice, linea in enumerate(lineas)
                    if not _es_linea_a_eliminar(
                        linea, lineas_repetidas, en_margen=indice in margenes
                    )
                ),
            )
        )
    return resultado


def _indices_de_margenes(lineas: list[str]) -> set[int]:
    """Índices de las primeras y últimas líneas no vacías, sin contar el espacio exterior."""
    no_vacias = [indice for indice, linea in enumerate(lineas) if linea.strip()]
    return set(no_vacias[:_LINEAS_POR_MARGEN] + no_vacias[-_LINEAS_POR_MARGEN:])


def _es_encabezado_articulo(linea: str) -> bool:
    """Protege los encabezados reconocidos por el chunker y los rótulos aislados sin signo."""
    return bool(PATRON_ARTICULO.match(linea) or _PATRON_ARTICULO_SIN_TERMINADOR.fullmatch(linea))


def _detectar_lineas_repetidas(paginas: list[PaginaExtraida]) -> set[str]:
    """Formas normalizadas repetidas en los márgenes de al menos la mitad de las páginas."""
    if len(paginas) < _MINIMO_PAGINAS_PARA_LIMPIAR:
        return set()

    paginas_por_linea_normalizada: dict[str, set[int]] = {}
    for pagina in paginas:
        lineas = pagina.texto.split("\n")
        normalizadas_en_esta_pagina: set[str] = set()
        for indice in _indices_de_margenes(lineas):
            linea = lineas[indice]
            if _es_encabezado_articulo(linea):
                continue
            normalizada = _normalizar_linea(linea)
            if not normalizada or normalizada in normalizadas_en_esta_pagina:
                continue
            normalizadas_en_esta_pagina.add(normalizada)
            paginas_por_linea_normalizada.setdefault(normalizada, set()).add(pagina.numero)

    umbral = len(paginas) * _FRACCION_MINIMA_DE_REPETICION
    return {
        normalizada
        for normalizada, numeros_de_pagina in paginas_por_linea_normalizada.items()
        if len(numeros_de_pagina) >= umbral
    }


def _es_linea_a_eliminar(linea: str, lineas_repetidas: set[str], *, en_margen: bool) -> bool:
    """Elimina numeración en cualquier posición y repeticiones solo dentro de los márgenes."""
    if _es_encabezado_articulo(linea):
        return False
    if _PATRON_NUMERACION_PAGINA.match(linea.strip()):
        return True
    return en_margen and _normalizar_linea(linea) in lineas_repetidas


def _normalizar_linea(linea: str) -> str:
    """Minúsculas, dígitos colapsados a `#` y espacios colapsados, para comparar líneas que
    difieren solo en el número de página o en espaciado.
    """
    sin_digitos = _PATRON_DIGITOS.sub("#", linea.strip().lower())
    return _PATRON_ESPACIOS.sub(" ", sin_digitos).strip()
