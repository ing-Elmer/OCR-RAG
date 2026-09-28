"""Fusión de búsqueda híbrida (vectorial + léxica) por Reciprocal Rank Fusion: función pura."""

from ocr_rag.core.schemas.documento import ChunkSimilar

# Constante estándar de RRF: amortigua el peso de las posiciones altas para que un candidato que
# aparece en varias listas (aunque no sea el primero de ninguna) pueda superar a uno que solo
# aparece en una.
CONSTANTE_RRF = 60


def fusionar_rrf(
    candidatos_vectoriales: list[ChunkSimilar],
    candidatos_lexicos: list[ChunkSimilar],
    top_k: int,
) -> list[ChunkSimilar]:
    """Combina dos listas de candidatos ya ordenadas por relevancia con Reciprocal Rank Fusion.

    Cada candidato suma `1 / (CONSTANTE_RRF + rank)` por cada lista en la que aparece (`rank`
    arranca en 1); un chunk presente en ambas listas suma los dos aportes y sube en el resultado
    final. Deduplica por chunk (mismo `documento_id` y `orden`) y devuelve los `top_k` con mayor
    score. Ante empate de score, se conserva el orden de aparición (desempate estable).
    """
    scores: dict[tuple[int, int], float] = {}
    chunk_por_clave: dict[tuple[int, int], ChunkSimilar] = {}
    orden_de_aparicion: dict[tuple[int, int], int] = {}
    siguiente_orden = 0

    for lista in (candidatos_vectoriales, candidatos_lexicos):
        for rank, chunk in enumerate(lista, start=1):
            clave = (chunk.documento_id, chunk.orden)
            scores[clave] = scores.get(clave, 0.0) + 1 / (CONSTANTE_RRF + rank)
            if clave not in chunk_por_clave:
                chunk_por_clave[clave] = chunk
                orden_de_aparicion[clave] = siguiente_orden
                siguiente_orden += 1

    claves_ordenadas = sorted(scores, key=lambda clave: (-scores[clave], orden_de_aparicion[clave]))
    return [chunk_por_clave[clave] for clave in claves_ordenadas[:top_k]]
