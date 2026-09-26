-- 006_create_ix_documento_archivo_sha256.sql
-- Índice sobre "ocr_documento_archivo.sha256" para resolver rápido si un archivo ya fue
-- cargado (idempotencia de `cli cargar-corpus`, y de futuras cargas por la API).
-- Idempotente: puede correrse más de una vez sin fallar.
-- Requiere que 003_create_documento_archivo.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

CREATE INDEX IF NOT EXISTS ix_ocr_documento_archivo_sha256
    ON ocr_rag.ocr_documento_archivo (sha256);

COMMIT;
