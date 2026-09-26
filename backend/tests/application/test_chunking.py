"""Tests del chunker (`application.chunking`), función pura."""

from ocr_rag.application.chunking import dividir_en_chunks
from ocr_rag.core.schemas.documento import PaginaExtraida


def test_dividir_en_chunks_texto_vacio_devuelve_lista_vacia() -> None:
    assert dividir_en_chunks([]) == []
    assert dividir_en_chunks([PaginaExtraida(numero=1, texto="   ")]) == []


def test_dividir_en_chunks_texto_corto_devuelve_un_unico_chunk() -> None:
    paginas = [PaginaExtraida(numero=1, texto="Hola mundo, este es un texto corto.")]

    chunks = dividir_en_chunks(paginas)

    assert len(chunks) == 1
    assert chunks[0].orden == 0
    assert chunks[0].contenido == "Hola mundo, este es un texto corto."
    assert chunks[0].pagina == 1


def test_dividir_en_chunks_texto_largo_respeta_tamano_y_genera_varios_chunks() -> None:
    # Frases cortas y repetidas para poder cortar en un límite de oración.
    texto = "Esta es una oración de prueba. " * 100
    paginas = [PaginaExtraida(numero=1, texto=texto)]

    chunks = dividir_en_chunks(paginas, tamano=200, solapamiento=50)

    assert len(chunks) > 1
    for chunk in chunks:
        # Un pequeño margen: el corte busca el mejor separador, no corta exacto.
        assert len(chunk.contenido) <= 200


def test_dividir_en_chunks_genera_solapamiento_entre_chunks_consecutivos() -> None:
    texto = "Palabra " * 400  # ~3200 caracteres, sin puntuación fuerte.
    paginas = [PaginaExtraida(numero=1, texto=texto)]

    chunks = dividir_en_chunks(paginas, tamano=200, solapamiento=50)

    assert len(chunks) > 1
    # El final del primer chunk y el principio del segundo comparten texto (solapamiento).
    cola_primero = chunks[0].contenido[-20:]
    assert cola_primero in chunks[1].contenido


def test_dividir_en_chunks_conserva_la_pagina_de_origen_de_cada_fragmento() -> None:
    paginas = [
        PaginaExtraida(numero=1, texto="Contenido de la primera página. " * 20),
        PaginaExtraida(numero=2, texto="Contenido de la segunda página. " * 20),
    ]

    chunks = dividir_en_chunks(paginas, tamano=300, solapamiento=50)

    paginas_de_chunks = {chunk.pagina for chunk in chunks}
    assert paginas_de_chunks == {1, 2}
    # El orden de los chunks respeta el orden de las páginas.
    assert chunks[0].pagina == 1
    assert chunks[-1].pagina == 2


def test_dividir_en_chunks_ignora_paginas_sin_texto() -> None:
    paginas = [
        PaginaExtraida(numero=1, texto="Texto real de la página uno."),
        PaginaExtraida(numero=2, texto="   "),
        PaginaExtraida(numero=3, texto="Texto real de la página tres."),
    ]

    chunks = dividir_en_chunks(paginas)

    contenido_total = " ".join(chunk.contenido for chunk in chunks)
    assert "página uno" in contenido_total
    assert "página tres" in contenido_total


def _texto_de_palabras(cantidad: int) -> str:
    """Texto sin puntos ni saltos: obliga a alinear el solapamiento por espacios."""
    return " ".join(f"palabra{indice:04d}" for indice in range(cantidad))


def test_dividir_en_chunks_ningun_fragmento_empieza_cortando_una_palabra() -> None:
    texto = _texto_de_palabras(600)
    palabras = set(texto.split(" "))

    chunks = dividir_en_chunks([PaginaExtraida(numero=1, texto=texto)], tamano=300, solapamiento=80)

    assert len(chunks) > 2
    for chunk in chunks:
        primera_palabra = chunk.contenido.split(" ")[0]
        assert primera_palabra in palabras, (
            f"el chunk {chunk.orden} empieza cortado: {primera_palabra!r}"
        )


def test_dividir_en_chunks_prefiere_empezar_el_solapamiento_en_una_oracion() -> None:
    oraciones = [f"Artículo {indice}. El régimen aplica a las mercancías." for indice in range(80)]
    texto = " ".join(oraciones)

    chunks = dividir_en_chunks(
        [PaginaExtraida(numero=1, texto=texto)], tamano=300, solapamiento=120
    )

    assert len(chunks) > 2
    for chunk in chunks[1:]:
        assert chunk.contenido.startswith(("Artículo", "El régimen")), chunk.contenido[:40]


def test_dividir_en_chunks_no_genera_un_fragmento_final_duplicado() -> None:
    texto = _texto_de_palabras(600)

    chunks = dividir_en_chunks([PaginaExtraida(numero=1, texto=texto)], tamano=300, solapamiento=80)

    ultimo, anteultimo = chunks[-1], chunks[-2]
    assert ultimo.contenido not in anteultimo.contenido
    assert texto.endswith(ultimo.contenido)


def test_dividir_en_chunks_token_sin_espacios_igual_avanza() -> None:
    texto = "x" * 2500

    chunks = dividir_en_chunks(
        [PaginaExtraida(numero=1, texto=texto)], tamano=1000, solapamiento=200
    )

    assert chunks
    assert "".join(chunk.contenido for chunk in chunks).count("x") >= 2500
