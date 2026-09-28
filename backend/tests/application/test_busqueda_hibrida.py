"""Tests de `application.busqueda_hibrida` (fusión RRF, función pura)."""

from ocr_rag.application.busqueda_hibrida import fusionar_rrf
from ocr_rag.core.schemas.documento import ChunkSimilar


def _chunk(documento_id: int, orden: int, contenido: str = "contenido") -> ChunkSimilar:
    return ChunkSimilar(
        documento_id=documento_id,
        nombre_archivo="a.pdf",
        orden=orden,
        pagina=1,
        contenido=contenido,
        similitud=0.5,
    )


def test_fusionar_rrf_sin_candidatos_devuelve_lista_vacia() -> None:
    assert fusionar_rrf([], [], top_k=5) == []


def test_fusionar_rrf_un_chunk_en_ambas_listas_sube_por_encima_de_uno_en_una_sola() -> None:
    chunk_en_ambas = _chunk(1, 0, "en ambas listas")
    chunk_solo_vectorial_primero = _chunk(2, 0, "solo vectorial, primero")
    chunk_solo_lexico_primero = _chunk(3, 0, "solo lexico, primero")

    vectoriales = [chunk_solo_vectorial_primero, chunk_en_ambas]
    lexicos = [chunk_solo_lexico_primero, chunk_en_ambas]

    resultado = fusionar_rrf(vectoriales, lexicos, top_k=5)

    # Aunque en ninguna lista individual está primero, la suma de los dos aportes de RRF lo pone
    # por encima de los que solo aparecen una vez.
    assert resultado[0].documento_id == 1


def test_fusionar_rrf_dedup_por_documento_id_y_orden() -> None:
    chunk = _chunk(1, 0)
    resultado = fusionar_rrf([chunk], [chunk], top_k=10)

    assert len(resultado) == 1


def test_fusionar_rrf_respeta_el_top_k() -> None:
    vectoriales = [_chunk(i, 0) for i in range(1, 6)]

    resultado = fusionar_rrf(vectoriales, [], top_k=2)

    assert len(resultado) == 2


def test_fusionar_rrf_conserva_el_orden_de_cada_lista_cuando_no_se_solapan() -> None:
    vectoriales = [_chunk(1, 0), _chunk(2, 0)]

    resultado = fusionar_rrf(vectoriales, [], top_k=5)

    assert [c.documento_id for c in resultado] == [1, 2]


def test_fusionar_rrf_desempate_estable_por_orden_de_aparicion() -> None:
    # `chunk_a` es primero en la lista vectorial y `chunk_b` es primero en la lexica: ambos
    # quedan con el mismo score (mismo rank, una sola lista cada uno). El empate se resuelve por
    # orden de aparición: como se procesa primero la lista vectorial, `chunk_a` queda primero.
    chunk_a = _chunk(1, 0)
    chunk_b = _chunk(2, 0)

    resultado = fusionar_rrf([chunk_a], [chunk_b], top_k=5)

    assert [c.documento_id for c in resultado] == [1, 2]
