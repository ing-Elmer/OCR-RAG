"""Chunking de texto extraído: función pura, sin I/O.

Divide el texto de un documento (ya extraído, página por página) en fragmentos de tamaño
acotado con solapamiento entre fragmentos consecutivos, cortando preferentemente en un límite
de párrafo u oración, y conservando la página de origen de cada fragmento.

Para documentos de tipo `"normativa"`, corta primero en los encabezados de artículo: un
fragmento nunca mezcla dos artículos, y los artículos largos se subdividen con la misma ventana
deslizante (todos sus sub-fragmentos comparten el número de artículo).
"""

import re

from ocr_rag.core.schemas.documento import ChunkTexto, PaginaExtraida, TipoDocumento

TAMANO_CHUNK = 1000
SOLAPAMIENTO = 200

# De más a menos preferido: párrafo, línea, fin de oración, espacio.
_SEPARADORES_DE_CORTE = ("\n\n", "\n", ". ", " ")

# Un corte antes de esta fracción de la ventana se descarta por generar fragmentos muy chicos.
_FRACCION_MINIMA_DE_VENTANA = 0.5

# Dónde puede empezar el solapamiento, de más a menos preferido: después de un párrafo, de una
# línea o de un fin de oración; en último caso, después de cualquier espacio (inicio de palabra).
_SEPARADORES_DE_INICIO = ("\n\n", "\n", ". ")

# Tipos de documento cuyo chunking corta en los encabezados de artículo.
_TIPOS_CON_ARTICULOS: frozenset[TipoDocumento] = frozenset({"normativa"})

# Encabezado a inicio de línea con terminador: "Artículo 94.", "Artículo 94.—", "Art. 94.",
# "ARTÍCULO 94 -" o "Artículo 94 bis:". Exigir el terminador evita cortar referencias como
# "artículo 94 de este Código" aunque el PDF las haya dejado al inicio de una línea.
# Los espacios horizontales impiden completar un supuesto encabezado con la línea siguiente.
PATRON_ARTICULO = re.compile(
    r"^[ \t]*(?:Art[íi]culo|Art\.)[ \t]+"
    r"(?P<numero>\d+(?:[ \t]*(?:bis|ter|quater))?)\b[ \t]*(?:\.[-—]?|[-—:])",
    re.MULTILINE | re.IGNORECASE,
)


def dividir_en_chunks(
    paginas: list[PaginaExtraida],
    *,
    tamano: int = TAMANO_CHUNK,
    solapamiento: int = SOLAPAMIENTO,
    tipo_documento: TipoDocumento | None = None,
) -> list[ChunkTexto]:
    """Concatena el texto de `paginas` (ignorando las que no tengan texto) y lo divide en
    fragmentos de ~`tamano` caracteres, con ~`solapamiento` caracteres de solapamiento entre
    fragmentos consecutivos. Cada fragmento conserva el número de página donde empieza.

    Si `tipo_documento` es `"normativa"`, primero separa el texto por encabezado de artículo
    (`PATRON_ARTICULO`): cada fragmento resultante lleva el número de artículo al que pertenece
    en `articulo`, y ninguno mezcla contenido de dos artículos. El texto anterior al primer
    artículo (considerandos, índice) y los demás tipos de documento quedan con `articulo=None`.
    """
    texto, offsets_de_pagina = _concatenar_con_offsets(paginas)
    if not texto:
        return []

    segmentos = (
        _segmentar_por_articulo(texto)
        if tipo_documento in _TIPOS_CON_ARTICULOS
        else [(None, 0, len(texto))]
    )

    chunks: list[ChunkTexto] = []
    orden = 0
    for articulo, inicio_segmento, fin_segmento in segmentos:
        orden = _dividir_ventanas(
            texto,
            offsets_de_pagina,
            inicio_segmento,
            fin_segmento,
            tamano,
            solapamiento,
            articulo,
            orden,
            chunks,
        )
    return chunks


def _segmentar_por_articulo(texto: str) -> list[tuple[str | None, int, int]]:
    """Divide `texto` en tramos `(articulo, inicio, fin)` según `PATRON_ARTICULO`.

    El primer tramo (si hay texto antes del primer artículo encontrado) lleva `articulo=None`.
    Si no se encuentra ningún encabezado de artículo, devuelve un único tramo con todo el texto.
    """
    coincidencias = list(PATRON_ARTICULO.finditer(texto))
    if not coincidencias:
        return [(None, 0, len(texto))]

    segmentos: list[tuple[str | None, int, int]] = []
    primer_inicio = coincidencias[0].start()
    if primer_inicio > 0:
        segmentos.append((None, 0, primer_inicio))

    for indice, coincidencia in enumerate(coincidencias):
        inicio = coincidencia.start()
        fin = coincidencias[indice + 1].start() if indice + 1 < len(coincidencias) else len(texto)
        numero = re.sub(r"\s+", " ", coincidencia.group("numero")).strip()
        segmentos.append((numero, inicio, fin))
    return segmentos


def _dividir_ventanas(
    texto: str,
    offsets_de_pagina: list[tuple[int, int]],
    inicio_segmento: int,
    fin_segmento: int,
    tamano: int,
    solapamiento: int,
    articulo: str | None,
    orden: int,
    chunks: list[ChunkTexto],
) -> int:
    """Aplica la ventana deslizante de `dividir_en_chunks` dentro de `[inicio_segmento,
    fin_segmento)`, agregando los fragmentos resultantes a `chunks`. Devuelve el próximo `orden`
    a usar (para que la numeración sea continua a través de los distintos segmentos/artículos).
    """
    inicio = inicio_segmento
    while inicio < fin_segmento:
        fin_maximo = min(inicio + tamano, fin_segmento)
        fin = fin_maximo if fin_maximo >= fin_segmento else _buscar_corte(texto, inicio, fin_maximo)
        fragmento = texto[inicio:fin].strip()
        if fragmento:
            pagina = _pagina_en_offset(offsets_de_pagina, inicio)
            chunks.append(
                ChunkTexto(orden=orden, contenido=fragmento, pagina=pagina, articulo=articulo)
            )
            orden += 1
        if fin >= fin_segmento:
            break
        siguiente_inicio = _alinear_inicio(texto, fin - solapamiento, fin, inicio_segmento)
        inicio = siguiente_inicio if siguiente_inicio > inicio else fin
    return orden


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


def _alinear_inicio(texto: str, desde: int, hasta: int, limite_inferior: int = 0) -> int:
    """Mueve el inicio del solapamiento hacia adelante hasta un límite natural.

    Busca en `[desde, hasta)` el primer inicio de párrafo, línea u oración; si no hay, el primer
    inicio de palabra. Así ningún fragmento empieza cortando una palabra por la mitad. Si la zona
    no tiene ningún espacio (un token enorme), devuelve `desde` sin cambios. `limite_inferior` es
    el inicio del segmento/artículo actual: nunca se retrocede antes de él.
    """
    if desde <= limite_inferior:
        return limite_inferior
    # Ya está justo al inicio de un párrafo, línea u oración.
    if texto[desde - 1] == "\n" or texto[max(limite_inferior, desde - 2) : desde] == ". ":
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
