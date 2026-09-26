"""Chunking de texto extraído: función pura, sin I/O.

Divide el texto de un documento (ya extraído, página por página) en fragmentos de tamaño
acotado con solapamiento entre fragmentos consecutivos, cortando preferentemente en un límite
de párrafo u oración, y conservando la página de origen de cada fragmento.
"""

from ocr_rag.core.schemas.documento import ChunkTexto, PaginaExtraida

TAMANO_CHUNK = 1000
SOLAPAMIENTO = 200

# De más a menos preferido: párrafo, línea, fin de oración, espacio.
_SEPARADORES_DE_CORTE = ("\n\n", "\n", ". ", " ")

# Un corte antes de esta fracción de la ventana se descarta por generar fragmentos muy chicos.
_FRACCION_MINIMA_DE_VENTANA = 0.5

# Dónde puede empezar el solapamiento, de más a menos preferido: después de un párrafo, de una
# línea o de un fin de oración; en último caso, después de cualquier espacio (inicio de palabra).
_SEPARADORES_DE_INICIO = ("\n\n", "\n", ". ")


def dividir_en_chunks(
    paginas: list[PaginaExtraida],
    *,
    tamano: int = TAMANO_CHUNK,
    solapamiento: int = SOLAPAMIENTO,
) -> list[ChunkTexto]:
    """Concatena el texto de `paginas` (ignorando las que no tengan texto) y lo divide en
    fragmentos de ~`tamano` caracteres, con ~`solapamiento` caracteres de solapamiento entre
    fragmentos consecutivos. Cada fragmento conserva el número de página donde empieza.
    """
    texto, offsets_de_pagina = _concatenar_con_offsets(paginas)
    if not texto:
        return []

    chunks: list[ChunkTexto] = []
    inicio = 0
    orden = 0
    largo_total = len(texto)
    while inicio < largo_total:
        fin_maximo = min(inicio + tamano, largo_total)
        fin = fin_maximo if fin_maximo >= largo_total else _buscar_corte(texto, inicio, fin_maximo)
        fragmento = texto[inicio:fin].strip()
        if fragmento:
            pagina = _pagina_en_offset(offsets_de_pagina, inicio)
            chunks.append(ChunkTexto(orden=orden, contenido=fragmento, pagina=pagina))
            orden += 1
        if fin >= largo_total:
            break
        siguiente_inicio = _alinear_inicio(texto, fin - solapamiento, fin)
        inicio = siguiente_inicio if siguiente_inicio > inicio else fin
    return chunks


def _concatenar_con_offsets(paginas: list[PaginaExtraida]) -> tuple[str, list[tuple[int, int]]]:
    """Junta el texto de las páginas no vacías y guarda en qué offset empieza cada una."""
    texto = ""
    offsets: list[tuple[int, int]] = []
    for pagina in paginas:
        contenido = pagina.texto.strip()
        if not contenido:
            continue
        if texto:
            texto += "\n\n"
        offsets.append((len(texto), pagina.numero))
        texto += contenido
    return texto, offsets


def _pagina_en_offset(offsets: list[tuple[int, int]], posicion: int) -> int | None:
    """Número de página cuyo offset de inicio es el último anterior (o igual) a `posicion`."""
    pagina_actual: int | None = None
    for offset_inicio, numero in offsets:
        if offset_inicio > posicion:
            break
        pagina_actual = numero
    return pagina_actual


def _buscar_corte(texto: str, inicio: int, fin: int) -> int:
    """Busca, dentro de la ventana `[inicio, fin)`, el mejor punto de corte antes de `fin`.

    Prueba los separadores de `_SEPARADORES_DE_CORTE` en orden de preferencia; si ninguno cae
    en la segunda mitad de la ventana (para no generar fragmentos demasiado chicos), corta
    exactamente en `fin`.
    """
    ventana = texto[inicio:fin]
    largo_minimo = int(len(ventana) * _FRACCION_MINIMA_DE_VENTANA)
    for separador in _SEPARADORES_DE_CORTE:
        posicion = ventana.rfind(separador)
        if posicion >= largo_minimo:
            return inicio + posicion + len(separador)
    return fin


def _alinear_inicio(texto: str, desde: int, hasta: int) -> int:
    """Mueve el inicio del solapamiento hacia adelante hasta un límite natural.

    Busca en `[desde, hasta)` el primer inicio de párrafo, línea u oración; si no hay, el primer
    inicio de palabra. Así ningún fragmento empieza cortando una palabra por la mitad. Si la zona
    no tiene ningún espacio (un token enorme), devuelve `desde` sin cambios.
    """
    if desde <= 0:
        return 0
    # Ya está justo al inicio de un párrafo, línea u oración.
    if texto[desde - 1] == "\n" or texto[max(0, desde - 2) : desde] == ". ":
        return desde
    zona = texto[desde:hasta]
    for separador in _SEPARADORES_DE_INICIO:
        posicion = zona.find(separador)
        if posicion != -1:
            return desde + posicion + len(separador)
    # Sin oraciones en la zona: al menos empezar en una palabra entera.
    if texto[desde - 1].isspace():
        return desde
    for indice, caracter in enumerate(zona):
        if caracter.isspace():
            return desde + indice + 1
    return desde
