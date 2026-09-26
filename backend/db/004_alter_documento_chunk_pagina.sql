-- 004_alter_documento_chunk_pagina.sql
-- Agrega a "ocr_documento_chunk" la página de origen del fragmento (chunking por página).
-- Idempotente: puede correrse más de una vez sin fallar.
-- Requiere que 001_create_schema_inicial.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

ALTER TABLE ocr_rag.ocr_documento_chunk
    ADD COLUMN IF NOT EXISTS pagina integer;

COMMENT ON COLUMN ocr_rag.ocr_documento_chunk.pagina IS
    'Número de página del documento donde empieza el fragmento; NULL si no aplica '
    '(por ejemplo, imágenes de una sola "página" lógica).';

COMMIT;
