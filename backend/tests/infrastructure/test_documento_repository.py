"""Regresión del SQL de búsqueda léxica, sin conectarse a una base de datos."""

from ocr_rag.infrastructure.repositories.documento_repository import (
    _COLUMNAS_CHUNK_SIMILAR,
    _SQL_BUSCAR_CANDIDATOS_LEXICOS,
)


def test_buscar_candidatos_lexicos_pregunta_natural_usa_or_parametrizado() -> None:
    sql = " ".join(_SQL_BUSCAR_CANDIDATOS_LEXICOS.split())
    consulta_or = "replace(plainto_tsquery('spanish', %(pregunta)s)::text, ' & ', ' | ')::tsquery"

    assert sql.startswith("WITH consulta AS MATERIALIZED ( SELECT " + consulta_or + " AS q )")
    assert sql.count("plainto_tsquery") == 1
    assert sql.count("%(pregunta)s") == 1
    assert sql.count("pregunta") == 1
    assert "websearch_to_tsquery" not in sql
    assert _COLUMNAS_CHUNK_SIMILAR in _SQL_BUSCAR_CANDIDATOS_LEXICOS
    assert "AND c.contenido_tsv @@ (SELECT q FROM consulta)" in sql
    assert "ORDER BY ts_rank_cd(c.contenido_tsv, (SELECT q FROM consulta)) DESC" in sql
    assert sql.endswith("LIMIT %(limite)s")
