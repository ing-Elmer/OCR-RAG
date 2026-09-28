-- 010_create_ix_documento_chunk_contenido_tsv.sql
-- Índice GIN sobre "ocr_documento_chunk.contenido_tsv", para la búsqueda léxica
-- (websearch_to_tsquery + ts_rank_cd) de la recuperación híbrida del RAG.
-- Idempotente: puede correrse más de una vez sin fallar.
-- Requiere que 009_alter_documento_chunk_articulo_tsv.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

CREATE INDEX IF NOT EXISTS ix_ocr_documento_chunk_contenido_tsv
    ON ocr_rag.ocr_documento_chunk USING GIN (contenido_tsv);

COMMIT;
