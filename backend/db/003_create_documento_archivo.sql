-- 003_create_documento_archivo.sql
-- Crea la tabla "ocr_documento_archivo": guarda el binario original de cada documento subido
-- (bytea), separado de "ocr_documento" para no traerlo en los listados.
-- Idempotente: puede correrse más de una vez sin duplicar objetos.
-- Requiere que 001_create_schema_inicial.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_documento_archivo (
    documento_id    bigint NOT NULL,
    contenido       bytea NOT NULL,
    tipo_contenido  varchar(100) NOT NULL,
    tamano_bytes    bigint NOT NULL,
    sha256          char(64),
    created_at      timestamptz NOT NULL DEFAULT now(),
    created_by      varchar(100),
    CONSTRAINT pk_ocr_documento_archivo PRIMARY KEY (documento_id),
    CONSTRAINT fk_ocr_documento_archivo_documento FOREIGN KEY (documento_id)
        REFERENCES ocr_rag.ocr_documento (id),
    CONSTRAINT ck_ocr_documento_archivo_tamano_bytes CHECK (tamano_bytes > 0)
);

COMMENT ON TABLE ocr_rag.ocr_documento_archivo IS
    'Binario original de cada documento subido (bytea); separada de ocr_documento para que los '
    'listados no lo carguen.';
COMMENT ON COLUMN ocr_rag.ocr_documento_archivo.contenido IS 'Archivo original tal como se subió.';
COMMENT ON COLUMN ocr_rag.ocr_documento_archivo.tipo_contenido IS
    'Content-Type declarado en la carga (application/pdf, image/png, image/jpeg, image/tiff).';
COMMENT ON COLUMN ocr_rag.ocr_documento_archivo.sha256 IS
    'Hash SHA-256 del contenido, en hexadecimal (64 caracteres).';

COMMIT;
