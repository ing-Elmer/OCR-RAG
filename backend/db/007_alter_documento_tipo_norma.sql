-- 007_alter_documento_tipo_norma.sql
-- Agrega a "ocr_documento" la categoría del documento (tipo_documento) y, si aplica, el nombre
-- de la norma o instrumento legal que representa (norma). "tipo_documento" se usa para filtrar
-- consultas y, en una fase posterior, para variar el chunking de las normas por artículo.
-- Idempotente: puede correrse más de una vez sin fallar.
-- Requiere que 001_create_schema_inicial.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

ALTER TABLE ocr_rag.ocr_documento
    ADD COLUMN IF NOT EXISTS tipo_documento varchar(30) NOT NULL DEFAULT 'otro',
    ADD COLUMN IF NOT EXISTS norma varchar(100);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_ocr_documento_tipo_documento'
    ) THEN
        ALTER TABLE ocr_rag.ocr_documento
            ADD CONSTRAINT ck_ocr_documento_tipo_documento
            CHECK (tipo_documento IN ('normativa', 'embarque', 'aduanero', 'contrato', 'otro'));
    END IF;
END $$;

COMMENT ON COLUMN ocr_rag.ocr_documento.tipo_documento IS
    'Categoría del documento: normativa | embarque | aduanero | contrato | otro. Si la carga no '
    'la indicó, el worker la completa clasificando el texto con el modelo de chat.';
COMMENT ON COLUMN ocr_rag.ocr_documento.norma IS
    'Nombre de la norma o instrumento legal que representa el documento (p. ej. "CAUCA IV"); '
    'NULL si no aplica o no se cargó.';

COMMIT;
