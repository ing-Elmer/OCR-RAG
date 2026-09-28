-- 008_create_ix_documento_tipo_documento.sql
-- Índice sobre "ocr_documento.tipo_documento", para filtrar consultas y listados por categoría.
-- Idempotente: puede correrse más de una vez sin fallar.
-- Requiere que 007_alter_documento_tipo_norma.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

CREATE INDEX IF NOT EXISTS ix_ocr_documento_tipo_documento
    ON ocr_rag.ocr_documento (tipo_documento);

COMMIT;
