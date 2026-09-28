-- 009_alter_documento_chunk_articulo_tsv.sql
-- Agrega a "ocr_documento_chunk" el número de artículo (chunking consciente de artículos para
-- documentos de tipo "normativa") y una columna generada de tsvector para la búsqueda léxica de
-- la recuperación híbrida del RAG.
-- Idempotente: puede correrse más de una vez sin fallar.
-- Requiere que 001_create_schema_inicial.sql y 004_alter_documento_chunk_pagina.sql ya se hayan
-- ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

ALTER TABLE ocr_rag.ocr_documento_chunk
    ADD COLUMN IF NOT EXISTS articulo varchar(20),
    ADD COLUMN IF NOT EXISTS contenido_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('spanish', contenido)) STORED;

COMMENT ON COLUMN ocr_rag.ocr_documento_chunk.articulo IS
    'Número de artículo de la norma al que pertenece el fragmento (p. ej. "94" o "94 bis"); '
    'NULL si el documento no es de tipo "normativa" o el fragmento es anterior al primer '
    'artículo (considerandos, índice).';
COMMENT ON COLUMN ocr_rag.ocr_documento_chunk.contenido_tsv IS
    'Vector de texto completo (idioma spanish) generado a partir de "contenido", usado por la '
    'búsqueda léxica de la recuperación híbrida (RRF) del RAG.';

COMMIT;
