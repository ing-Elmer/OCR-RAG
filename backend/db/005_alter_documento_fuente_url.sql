-- 005_alter_documento_fuente_url.sql
-- Agrega a "ocr_documento" la URL de origen del documento, para las fuentes cargadas por el
-- comando `python -m ocr_rag.cli cargar-corpus` (carga masiva del corpus normativo). Las cargas
-- manuales por la API dejan esta columna en NULL.
-- Idempotente: puede correrse más de una vez sin fallar.
-- Requiere que 001_create_schema_inicial.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

ALTER TABLE ocr_rag.ocr_documento
    ADD COLUMN IF NOT EXISTS fuente_url varchar(1000);

COMMENT ON COLUMN ocr_rag.ocr_documento.fuente_url IS
    'URL de origen del documento, cuando se cargó desde una fuente externa (cli cargar-corpus). '
    'NULL en las cargas manuales por la API.';

COMMIT;
