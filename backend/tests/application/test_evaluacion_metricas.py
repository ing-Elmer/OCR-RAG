"""Tests de las métricas puras de evaluación del RAG (`application/evaluacion_metricas.py`)."""

from ocr_rag.application.evaluacion_metricas import (
    ResultadoRecuperacion,
    calcular_resumen,
    cita_articulo,
    cita_atribuible_a_norma,
    contar_citas,
    evaluar_recuperacion,
    posicion_recuperado,
    respuesta_indica_sin_informacion,
)
from ocr_rag.core.schemas.documento import FuenteConsulta
from ocr_rag.core.schemas.evaluacion import ArticuloEsperado


def _fuente(norma: str | None, articulo: str | None) -> FuenteConsulta:
    return FuenteConsulta(
        documento_id=1,
        nombre_archivo="cauca-iv.pdf",
        orden=0,
        pagina=1,
        fragmento="texto de prueba",
        similitud=0.9,
        tipo_documento="normativa",
        norma=norma,
        articulo=articulo,
    )


# --- posicion_recuperado -----------------------------------------------------------------


def test_posicion_recuperado_devuelve_la_posicion_1_based_de_la_primera_coincidencia() -> None:
    esperados = [ArticuloEsperado(norma="CAUCA IV", articulo="94")]
    fuentes = [_fuente("RECAUCA IV", "395"), _fuente("CAUCA IV", "94")]

    assert posicion_recuperado(esperados, fuentes) == 2


def test_posicion_recuperado_normaliza_espacios_y_mayusculas() -> None:
    esperados = [ArticuloEsperado(norma="cauca iv", articulo=" 94 ")]
    fuentes = [_fuente("  CAUCA IV  ", "94")]

    assert posicion_recuperado(esperados, fuentes) == 1


def test_posicion_recuperado_sin_coincidencias_devuelve_none() -> None:
    esperados = [ArticuloEsperado(norma="CAUCA IV", articulo="94")]
    fuentes = [_fuente("RECAUCA IV", "395")]

    assert posicion_recuperado(esperados, fuentes) is None


def test_posicion_recuperado_no_confunde_normas_distintas_con_el_mismo_articulo() -> None:
    esperados = [ArticuloEsperado(norma="CAUCA IV", articulo="94")]
    fuentes = [_fuente("RECAUCA IV", "94")]

    assert posicion_recuperado(esperados, fuentes) is None


def test_posicion_recuperado_ignora_fuentes_sin_norma_o_articulo() -> None:
    esperados = [ArticuloEsperado(norma="CAUCA IV", articulo="94")]
    fuentes = [_fuente(None, None)]

    assert posicion_recuperado(esperados, fuentes) is None


# --- cita_articulo -----------------------------------------------------------------------


def test_cita_articulo_reconoce_variantes_de_articulo() -> None:
    assert cita_articulo("94", "Ver el Art. 94 del CAUCA IV")
    assert cita_articulo("94", "Ver el Artículo 94 del CAUCA IV")
    assert cita_articulo("94", "ver el articulo 94 del cauca iv")


def test_cita_articulo_no_confunde_94_con_194() -> None:
    assert not cita_articulo("94", "Ver el Artículo 194 del RECAUCA IV")


def test_cita_articulo_no_matchea_si_no_esta_presente() -> None:
    assert not cita_articulo("94", "No hay ninguna referencia a otro artículo aquí")


# --- cita_atribuible_a_norma ---------------------------------------------------------------


def test_cita_atribuible_a_norma_con_otra_norma_cerca_no_atribuye() -> None:
    esperado = ArticuloEsperado(norma="CAUCA IV", articulo="94")

    # "CAUCA IV" es substring de "RECAUCA IV": no debe confundirse con la norma esperada.
    assert not cita_atribuible_a_norma(esperado, "Ver el Art. 94 del RECAUCA IV", [])


def test_cita_atribuible_a_norma_con_la_norma_correcta_cerca_atribuye() -> None:
    esperado = ArticuloEsperado(norma="CAUCA IV", articulo="94")

    assert cita_atribuible_a_norma(esperado, "Ver el Art. 94 del CAUCA IV", [])


def test_cita_atribuible_a_norma_sin_la_edicion_atribuye() -> None:
    # Regresión de la evaluación real: el modelo escribe "Art. 52 del CAUCA" y "Art. 333 del
    # RECAUCA" (sin "IV"), que son citas correctas y antes se contaban como fallidas.
    assert cita_atribuible_a_norma(
        ArticuloEsperado(norma="CAUCA IV", articulo="52"),
        "Según el Art. 52 del CAUCA, las formas de garantía incluyen fianza.",
        [],
    )
    assert cita_atribuible_a_norma(
        ArticuloEsperado(norma="RECAUCA IV", articulo="333"),
        "Según el Art. 333 del RECAUCA, los sujetos pueden rectificar.",
        [],
    )


def test_cita_atribuible_a_norma_sin_la_edicion_no_confunde_cauca_con_recauca() -> None:
    esperado = ArticuloEsperado(norma="CAUCA IV", articulo="99")

    assert not cita_atribuible_a_norma(esperado, "según el Artículo 99 del RECAUCA.", [])


def test_cita_atribuible_a_norma_por_referencia_de_fuente_atribuye() -> None:
    esperado = ArticuloEsperado(norma="CAUCA IV", articulo="94")
    fuentes = [_fuente("RECAUCA IV", "395"), _fuente("CAUCA IV", "94")]

    assert cita_atribuible_a_norma(esperado, "Ver el Art. 94 [2]", fuentes)


def test_cita_atribuible_a_norma_referencia_de_fuente_que_no_coincide_no_atribuye() -> None:
    esperado = ArticuloEsperado(norma="CAUCA IV", articulo="94")
    fuentes = [_fuente("RECAUCA IV", "395")]

    assert not cita_atribuible_a_norma(esperado, "Ver el Art. 94 [1]", fuentes)


def test_cita_atribuible_a_norma_no_confunde_94_con_194() -> None:
    esperado = ArticuloEsperado(norma="CAUCA IV", articulo="94")

    assert not cita_atribuible_a_norma(esperado, "Ver el Art. 194 del CAUCA IV", [])


# --- respuesta_indica_sin_informacion --------------------------------------------------


def test_respuesta_indica_sin_informacion_reconoce_el_mensaje_fijo() -> None:
    assert respuesta_indica_sin_informacion(
        "No encontré información relevante en los documentos cargados."
    )


def test_respuesta_indica_sin_informacion_con_respuesta_normal_es_falso() -> None:
    assert not respuesta_indica_sin_informacion("El tránsito aduanero es... [1]")


# --- contar_citas --------------------------------------------------------------------------


def test_contar_citas_cuenta_los_esperados_citados() -> None:
    esperados = [
        ArticuloEsperado(norma="CAUCA IV", articulo="94"),
        ArticuloEsperado(norma="CAUCA IV", articulo="95"),
    ]
    fuentes = [_fuente("CAUCA IV", "94")]

    logradas, total = contar_citas(esperados, "Ver el Art. 94 [1], pero no el otro", fuentes)

    assert (logradas, total) == (1, 2)


def test_contar_citas_de_caso_negativo_es_0_de_0() -> None:
    assert contar_citas([], "No encontré información relevante.", []) == (0, 0)


# --- evaluar_recuperacion --------------------------------------------------------------


def test_evaluar_recuperacion_caso_positivo_con_acierto() -> None:
    esperados = [ArticuloEsperado(norma="CAUCA IV", articulo="94")]
    fuentes = [_fuente("CAUCA IV", "94")]

    resultado = evaluar_recuperacion(esperados, fuentes, "El tránsito aduanero es... [1]")

    assert resultado == ResultadoRecuperacion(acierto=True, posicion=1)


def test_evaluar_recuperacion_caso_positivo_sin_acierto() -> None:
    esperados = [ArticuloEsperado(norma="CAUCA IV", articulo="94")]

    resultado = evaluar_recuperacion(esperados, [], "No encontré información.")

    assert resultado == ResultadoRecuperacion(acierto=False, posicion=None)


def test_evaluar_recuperacion_caso_negativo_sin_fuentes_es_acierto() -> None:
    resultado = evaluar_recuperacion([], [], "No encontré información relevante.")

    assert resultado == ResultadoRecuperacion(acierto=True, posicion=1)


def test_evaluar_recuperacion_caso_negativo_con_respuesta_que_avisa_es_acierto() -> None:
    fuentes = [_fuente("CAUCA IV", "1")]

    resultado = evaluar_recuperacion([], fuentes, "No dispongo de información sobre eso.")

    assert resultado == ResultadoRecuperacion(acierto=True, posicion=1)


def test_evaluar_recuperacion_caso_negativo_que_inventa_una_respuesta_no_es_acierto() -> None:
    fuentes = [_fuente("CAUCA IV", "1")]

    resultado = evaluar_recuperacion([], fuentes, "La respuesta es que sí, según el Art. 1 [1]")

    assert resultado == ResultadoRecuperacion(acierto=False, posicion=None)


# --- calcular_resumen ------------------------------------------------------------------


def test_calcular_resumen_hit_at_k_y_mrr() -> None:
    recuperaciones = [
        ResultadoRecuperacion(acierto=True, posicion=1),
        ResultadoRecuperacion(acierto=True, posicion=4),
        ResultadoRecuperacion(acierto=False, posicion=None),
    ]
    citas = [(1, 1), (0, 1), (0, 1)]

    resumen = calcular_resumen(recuperaciones, citas)

    assert resumen.hit_at_k == 2 / 3
    assert resumen.mrr == (1 + 0.25 + 0) / 3
    assert resumen.porcentaje_citas_completas == 1 / 3


def test_calcular_resumen_sin_casos_devuelve_ceros() -> None:
    resumen = calcular_resumen([], [])

    assert resumen.hit_at_k == 0.0
    assert resumen.mrr == 0.0
    assert resumen.porcentaje_citas_completas == 0.0


def test_calcular_resumen_todos_los_aciertos_dan_metricas_perfectas() -> None:
    recuperaciones = [
        ResultadoRecuperacion(acierto=True, posicion=1),
        ResultadoRecuperacion(acierto=True, posicion=1),
    ]
    citas = [(1, 1), (2, 2)]

    resumen = calcular_resumen(recuperaciones, citas)

    assert resumen.hit_at_k == 1.0
    assert resumen.mrr == 1.0
    assert resumen.porcentaje_citas_completas == 1.0
