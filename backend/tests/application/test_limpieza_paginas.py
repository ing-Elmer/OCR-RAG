"""Tests de `application.limpieza_paginas` (función pura)."""

import pytest

from ocr_rag.application.limpieza_paginas import limpiar_encabezados_pies
from ocr_rag.core.schemas.documento import PaginaExtraida

# Marcas de contenido "único" por página que no incluyen dígitos: si incluyeran el número de
# página, la normalización de dígitos (que es intencional, para detectar "Página 1 de 4" /
# "Página 2 de 4" como la misma línea) las confundiría entre sí.
_MARCAS_UNICAS = ("alfa", "beta", "gamma", "delta", "épsilon")


def _paginas(cantidad: int, encabezado: str = "CAUCA IV") -> list[PaginaExtraida]:
    paginas = []
    for i in range(1, cantidad + 1):
        marca = _MARCAS_UNICAS[i - 1]
        texto = f"{encabezado}\nPágina {i} de {cantidad}\nContenido único {marca}."
        paginas.append(PaginaExtraida(numero=i, texto=texto))
    return paginas


def test_limpiar_encabezados_pies_con_menos_de_cuatro_paginas_quita_solo_numeracion() -> None:
    paginas = _paginas(3)

    resultado = limpiar_encabezados_pies(paginas)

    assert resultado == [
        PaginaExtraida(numero=i, texto=f"CAUCA IV\nContenido único {_MARCAS_UNICAS[i - 1]}.")
        for i in range(1, 4)
    ]


def test_limpiar_encabezados_pies_quita_encabezado_repetido_en_todas_las_paginas() -> None:
    paginas = _paginas(4)

    resultado = limpiar_encabezados_pies(paginas)

    for pagina in resultado:
        assert "CAUCA IV" not in pagina.texto


def test_limpiar_encabezados_pies_quita_numeracion_de_pagina() -> None:
    paginas = _paginas(4)

    resultado = limpiar_encabezados_pies(paginas)

    for pagina in resultado:
        assert "Página" not in pagina.texto
        assert "de 4" not in pagina.texto


def test_limpiar_encabezados_pies_conserva_el_contenido_unico_de_cada_pagina() -> None:
    paginas = _paginas(4)

    resultado = limpiar_encabezados_pies(paginas)

    for i, pagina in enumerate(resultado, start=1):
        assert f"Contenido único {_MARCAS_UNICAS[i - 1]}." in pagina.texto


def test_limpiar_encabezados_pies_no_borra_lineas_legitimas_que_se_repiten_pocas_veces() -> None:
    paginas = [
        PaginaExtraida(numero=1, texto="Nota introductoria exclusiva de la página uno."),
        PaginaExtraida(numero=2, texto="Artículo 2. Otro contenido distinto."),
        PaginaExtraida(numero=3, texto="Artículo 3. Contenido totalmente distinto."),
        PaginaExtraida(numero=4, texto="Artículo 4. Más contenido distinto todavía."),
    ]

    resultado = limpiar_encabezados_pies(paginas)

    # Una línea que aparece en una sola página (1 de 4 = 25%, por debajo del umbral) no es un
    # encabezado/pie: se conserva.
    assert "Nota introductoria exclusiva de la página uno." in resultado[0].texto
    assert "Artículo 2. Otro contenido distinto." in resultado[1].texto


def test_limpiar_encabezados_pies_quita_linea_repetida_justo_en_la_mitad_de_las_paginas() -> None:
    paginas = [
        PaginaExtraida(numero=1, texto="Aviso de confidencialidad\nContenido único uno."),
        PaginaExtraida(numero=2, texto="Aviso de confidencialidad\nContenido único dos."),
        PaginaExtraida(numero=3, texto="Contenido único tres."),
        PaginaExtraida(numero=4, texto="Contenido único cuatro."),
    ]

    resultado = limpiar_encabezados_pies(paginas)

    # Se repite en exactamente el 50% de las páginas: el umbral es "≥ 50%", así que se elimina.
    assert "Aviso de confidencialidad" not in resultado[0].texto
    assert "Aviso de confidencialidad" not in resultado[1].texto
    assert "Contenido único uno." in resultado[0].texto


def test_limpiar_encabezados_pies_reconoce_variantes_de_numeracion() -> None:
    variantes = ["Página 130 de 215", "Pág. 12", "- 12 -", "12 / 215", "12 de 215"]
    paginas = [
        PaginaExtraida(
            numero=i,
            texto=f"CAUCA IV\n{variante}\nContenido único {i}.",
        )
        for i, variante in enumerate(variantes, start=1)
    ]

    resultado = limpiar_encabezados_pies(paginas)

    for pagina, variante in zip(resultado, variantes, strict=True):
        assert variante not in pagina.texto


@pytest.mark.parametrize(
    "encabezado",
    [
        "ARTÍCULO {numero}",
        "ARTÍCULO {numero}. Disposiciones generales.",
        "Artículo {numero} bis. Disposiciones complementarias.",
        "Artículo {numero} ter. Disposiciones complementarias.",
        "Artículo {numero} quater. Disposiciones complementarias.",
        "Art. {numero}. Disposiciones generales.",
        "Artículo {numero}.- Disposiciones generales.",
        "Artículo {numero}.— Disposiciones generales.",
        "Artículo {numero} - Disposiciones generales.",
        "Artículo {numero} — Disposiciones generales.",
        "Artículo {numero}: Disposiciones generales.",
    ],
)
def test_limpiar_encabezados_pies_articulos_en_cuatro_paginas_conserva_encabezados(
    encabezado: str,
) -> None:
    paginas = [
        PaginaExtraida(
            numero=i,
            texto=f"{encabezado.format(numero=i)}\nContenido único {_MARCAS_UNICAS[i - 1]}.",
        )
        for i in range(1, 5)
    ]

    resultado = limpiar_encabezados_pies(paginas)

    assert resultado == paginas


def test_limpiar_encabezados_pies_repeticion_solo_interior_conserva_contenido() -> None:
    paginas = [
        PaginaExtraida(
            numero=i,
            texto="\n".join(
                [f"Inicio {marca} {j}" for j in range(3)]
                + ["Las mercancías están sujetas a control aduanero."]
                + [f"Final {marca} {j}" for j in range(3)]
            ),
        )
        for i, marca in enumerate(_MARCAS_UNICAS[:4], start=1)
    ]

    resultado = limpiar_encabezados_pies(paginas)

    assert resultado == paginas


def test_limpiar_encabezados_pies_repeticiones_fuera_del_margen_no_cuentan_para_umbral() -> None:
    paginas = []
    for i, marca in enumerate(_MARCAS_UNICAS[:4], start=1):
        lineas = [f"Contenido {marca} {j}" for j in range(6)]
        lineas.insert(0 if i == 1 else 3, "Disposición común para las mercancías.")
        paginas.append(PaginaExtraida(numero=i, texto="\n".join(lineas)))

    resultado = limpiar_encabezados_pies(paginas)

    assert resultado == paginas


def test_limpiar_encabezados_pies_misma_linea_en_margen_y_cuerpo_conserva_solo_interior() -> None:
    paginas = [
        PaginaExtraida(
            numero=i,
            texto=(
                f"RECAUCA IV\nInicio {marca}\nContinuación {marca}\nRECAUCA IV\n"
                f"Disposición {marca}\nFinal {marca}\nSitio oficial de la aduana"
            ),
        )
        for i, marca in enumerate(_MARCAS_UNICAS[:4], start=1)
    ]

    resultado = limpiar_encabezados_pies(paginas)

    for pagina, marca in zip(resultado, _MARCAS_UNICAS[:4], strict=True):
        assert pagina.texto == (
            f"Inicio {marca}\nContinuación {marca}\nRECAUCA IV\nDisposición {marca}\nFinal {marca}"
        )


def test_limpiar_encabezados_pies_margenes_con_lineas_vacias_elimina_encabezado_y_pie() -> None:
    paginas = [
        PaginaExtraida(
            numero=i,
            texto=(
                f"\n\n\n\nInicio {marca}\n\nSigue {marca}\n\nCAUCA IV\n"
                "Texto repetido del cuerpo que debe conservarse.\n"
                f"Sitio oficial de la aduana\n\nFinal {marca}\nFin {marca}\n\n\n\n"
            ),
        )
        for i, marca in enumerate(_MARCAS_UNICAS[:4], start=1)
    ]

    resultado = limpiar_encabezados_pies(paginas)

    for original, limpia in zip(paginas, resultado, strict=True):
        assert limpia.numero == original.numero
        assert limpia.texto == original.texto.replace("CAUCA IV\n", "").replace(
            "Sitio oficial de la aduana\n", ""
        )


@pytest.mark.parametrize("numeracion", ["Página 130 de 215", "- 12 -", "12 / 215"])
def test_limpiar_encabezados_pies_numeracion_interior_en_una_pagina_siempre_elimina(
    numeracion: str,
) -> None:
    anteriores = "Inicio\nSiguiente\nOtra línea"
    posteriores = "Más contenido\nContinúa\nFinal"
    paginas = [
        PaginaExtraida(numero=1, texto=f"{anteriores}\n{numeracion}\n{posteriores}"),
    ]

    resultado = limpiar_encabezados_pies(paginas)

    assert resultado == [PaginaExtraida(numero=1, texto=f"{anteriores}\n{posteriores}")]
