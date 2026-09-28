"""Tests del chunker (`application.chunking`), función pura."""

import pytest

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


def test_dividir_en_chunks_normativa_separa_fragmentos_por_articulo() -> None:
    texto = (
        "Artículo 94. Tránsito aduanero. Es el régimen mediante el cual las mercancías son "
        "transportadas bajo control aduanero.\n\n"
        "Artículo 95. Base de datos regional. Los países mantienen información compartida sobre "
        "las operaciones de tránsito."
    )
    paginas = [PaginaExtraida(numero=1, texto=texto)]

    chunks = dividir_en_chunks(paginas, tipo_documento="normativa")

    assert [chunk.articulo for chunk in chunks] == ["94", "95"]
    assert "Artículo 95" not in chunks[0].contenido
    assert "Artículo 94" not in chunks[1].contenido


def test_dividir_en_chunks_normativa_no_corta_por_referencias_dentro_del_texto() -> None:
    texto = (
        "Artículo 94. Tránsito aduanero. Según el artículo 94 de este Código, la mercancía "
        "circula bajo control aduanero hasta su destino.\n\n"
        "Artículo 95. Base de datos regional. Se aplica lo dispuesto en el artículo 94 anterior."
    )
    paginas = [PaginaExtraida(numero=1, texto=texto)]

    chunks = dividir_en_chunks(paginas, tipo_documento="normativa")

    assert [chunk.articulo for chunk in chunks] == ["94", "95"]
    assert "artículo 94 anterior" in chunks[1].contenido


def test_dividir_en_chunks_normativa_texto_previo_al_primer_articulo_queda_sin_articulo() -> None:
    texto = (
        "CONSIDERANDO: que es necesario actualizar el marco jurídico regional.\n\n"
        "Artículo 1. Objeto. Este Código regula el régimen aduanero centroamericano."
    )
    paginas = [PaginaExtraida(numero=1, texto=texto)]

    chunks = dividir_en_chunks(paginas, tipo_documento="normativa")

    assert chunks[0].articulo is None
    assert "CONSIDERANDO" in chunks[0].contenido
    assert chunks[1].articulo == "1"


def test_dividir_en_chunks_normativa_articulo_largo_se_subdivide_con_el_mismo_numero() -> None:
    texto = "Artículo 94. Tránsito aduanero. " + "El régimen aplica a las mercancías. " * 40

    chunks = dividir_en_chunks(
        [PaginaExtraida(numero=1, texto=texto)],
        tamano=300,
        solapamiento=60,
        tipo_documento="normativa",
    )

    assert len(chunks) > 1
    assert all(chunk.articulo == "94" for chunk in chunks)


def test_dividir_en_chunks_normativa_reconoce_articulo_bis() -> None:
    texto = (
        "Artículo 94. Tránsito aduanero. Definición general.\n\n"
        "Artículo 94 bis. Tránsito aduanero especial. Régimen complementario aplicable."
    )
    paginas = [PaginaExtraida(numero=1, texto=texto)]

    chunks = dividir_en_chunks(paginas, tipo_documento="normativa")

    assert [chunk.articulo for chunk in chunks] == ["94", "94 bis"]


def test_dividir_en_chunks_no_normativa_no_asigna_articulo() -> None:
    texto = "Artículo 94. Esto es un contrato que menciona un artículo pero no es normativa. " * 5
    paginas = [PaginaExtraida(numero=1, texto=texto)]

    chunks = dividir_en_chunks(paginas, tipo_documento="contrato")

    assert all(chunk.articulo is None for chunk in chunks)


def test_dividir_en_chunks_token_sin_espacios_igual_avanza() -> None:
    texto = "x" * 2500

    chunks = dividir_en_chunks(
        [PaginaExtraida(numero=1, texto=texto)], tamano=1000, solapamiento=200
    )

    assert chunks
    assert "".join(chunk.contenido for chunk in chunks).count("x") >= 2500


def test_dividir_en_chunks_referencia_partida_conserva_el_articulo_95() -> None:
    articulo_95 = (
        "Artículo 95. Base de datos regional. Se aplica lo previsto en el\n"
        "artículo 94 de este Código a las operaciones de tránsito."
    )
    articulo_96 = "Artículo 96. Control. Las aduanas verifican las operaciones."
    paginas = [PaginaExtraida(numero=1, texto=f"{articulo_95}\n\n{articulo_96}")]

    chunks = dividir_en_chunks(paginas, tipo_documento="normativa")

    assert [chunk.articulo for chunk in chunks] == ["95", "96"]
    assert [chunk.contenido for chunk in chunks] == [articulo_95, articulo_96]


@pytest.mark.parametrize(
    "referencia",
    [
        "artículos 12 y 13",
        "artículo 94, inciso a)",
        "artículo 5 del presente Reglamento",
        "artículo 94 de este Código",
        "artículo 94 y siguientes",
        "artículo 94) de este Código",
        "artículo 94 inciso a)",
        "artículo 94 literal a)",
        "artículo 94 numeral 1",
        "artículo 94 párrafo segundo",
        "artículo 94 bis del presente Reglamento",
    ],
)
def test_dividir_en_chunks_referencia_al_inicio_de_linea_no_corta(referencia: str) -> None:
    texto = f"Artículo 95. Disposiciones. Se aplica lo previsto en el\n{referencia}."

    chunks = dividir_en_chunks([PaginaExtraida(numero=1, texto=texto)], tipo_documento="normativa")

    assert [chunk.articulo for chunk in chunks] == ["95"]
    assert chunks[0].contenido == texto


@pytest.mark.parametrize(
    ("encabezado", "numero"),
    [
        ("Artículo 94. Tránsito aduanero", "94"),
        ("Artículo 94.\nTránsito aduanero", "94"),
        ("Artículo 395. Inicio del plazo. El cómputo del plazo comienza hoy.", "395"),
        ("Artículo 94 bis. Disposición complementaria.", "94 bis"),
        ("Artículo 94 ter. Disposición complementaria.", "94 ter"),
        ("Artículo 94 quater. Disposición complementaria.", "94 quater"),
        ("ARTÍCULO 94. TRÁNSITO ADUANERO", "94"),
        ("Art. 94. Tránsito aduanero", "94"),
        ("\tArtículo\t94\t bis. Tránsito aduanero especial", "94 bis"),
    ],
)
def test_dividir_en_chunks_encabezado_valido_abre_segmento(encabezado: str, numero: str) -> None:
    texto_previo = "Artículo 93. Disposición anterior."
    texto = f"{texto_previo}\n\n{encabezado}"

    chunks = dividir_en_chunks([PaginaExtraida(numero=1, texto=texto)], tipo_documento="normativa")

    assert [chunk.articulo for chunk in chunks] == ["93", numero]
    assert [chunk.contenido for chunk in chunks] == [texto_previo, encabezado.strip()]


@pytest.mark.parametrize("terminador", [".", ".-", ".—", "-", "—", ":"])
def test_dividir_en_chunks_encabezado_con_terminador_abre_segmento(terminador: str) -> None:
    articulo_94 = f"Artículo 94{terminador} Tránsito aduanero."
    articulo_95 = "Artículo 95. Base de datos regional."

    chunks = dividir_en_chunks(
        [PaginaExtraida(numero=1, texto=f"{articulo_94}\n{articulo_95}")],
        tipo_documento="normativa",
    )

    assert [chunk.articulo for chunk in chunks] == ["94", "95"]
    assert [chunk.contenido for chunk in chunks] == [articulo_94, articulo_95]


@pytest.mark.parametrize(
    "referencia",
    ["artículo\n94. de este Código", "artículo 94\n. de este Código", "artículo 94\nbis."],
)
def test_dividir_en_chunks_encabezado_incompleto_no_consume_salto_de_linea(referencia: str) -> None:
    texto = f"Artículo 95. Disposiciones. Se aplica el\n{referencia}"

    chunks = dividir_en_chunks([PaginaExtraida(numero=1, texto=texto)], tipo_documento="normativa")

    assert [chunk.articulo for chunk in chunks] == ["95"]
    assert chunks[0].contenido == texto
