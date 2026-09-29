-- 001_create_schema_inicial.sql
-- Crea el schema "ocr_rag" y las tablas base: usuarios/roles/permisos, refresh tokens y el
-- modelo de documentos + chunks con embeddings (pgvector) para RAG.
-- Idempotente: puede correrse más de una vez sin duplicar objetos.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

CREATE SCHEMA IF NOT EXISTS ocr_rag;

-- Necesaria para la columna `embedding vector(1536)` de ocr_documento_chunk.
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================================================
-- Usuarios, roles y permisos
-- =====================================================================================

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_usuario (
    id               bigint GENERATED ALWAYS AS IDENTITY,
    username         varchar(100) NOT NULL,
    password_hash    text NOT NULL,
    nombre_completo  varchar(200) NOT NULL,
    activo           boolean NOT NULL DEFAULT true,
    created_at       timestamptz NOT NULL DEFAULT now(),
    created_by       varchar(100),
    updated_at       timestamptz,
    updated_by       varchar(100),
    CONSTRAINT pk_ocr_usuario PRIMARY KEY (id),
    CONSTRAINT uq_ocr_usuario_username UNIQUE (username)
);

COMMENT ON TABLE ocr_rag.ocr_usuario IS 'Usuarios propios del sistema (autenticación con JWT).';
COMMENT ON COLUMN ocr_rag.ocr_usuario.password_hash IS 'Hash bcrypt de la contraseña; nunca texto plano.';
COMMENT ON COLUMN ocr_rag.ocr_usuario.activo IS 'Usuario inactivo no puede autenticarse ni resolverse en /api/me.';

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_rol (
    id          bigint GENERATED ALWAYS AS IDENTITY,
    codigo      varchar(50) NOT NULL,
    nombre      varchar(150) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  varchar(100),
    updated_at  timestamptz,
    updated_by  varchar(100),
    CONSTRAINT pk_ocr_rol PRIMARY KEY (id),
    CONSTRAINT uq_ocr_rol_codigo UNIQUE (codigo)
);

COMMENT ON TABLE ocr_rag.ocr_rol IS 'Catálogo de roles asignables a usuarios.';
COMMENT ON COLUMN ocr_rag.ocr_rol.codigo IS 'Código estable del rol, usado por la aplicación (p. ej. ADMIN).';

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_permiso (
    id          bigint GENERATED ALWAYS AS IDENTITY,
    codigo      varchar(100) NOT NULL,
    nombre      varchar(150) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  varchar(100),
    updated_at  timestamptz,
    updated_by  varchar(100),
    CONSTRAINT pk_ocr_permiso PRIMARY KEY (id),
    CONSTRAINT uq_ocr_permiso_codigo UNIQUE (codigo)
);

COMMENT ON TABLE ocr_rag.ocr_permiso IS 'Catálogo de permisos, usados por require_permission() en la API.';
COMMENT ON COLUMN ocr_rag.ocr_permiso.codigo IS 'Código estable del permiso, usado por la aplicación (p. ej. DOCUMENTO_VER).';

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_usuario_rol (
    usuario_id  bigint NOT NULL,
    rol_id      bigint NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  varchar(100),
    CONSTRAINT pk_ocr_usuario_rol PRIMARY KEY (usuario_id, rol_id),
    CONSTRAINT fk_ocr_usuario_rol_usuario FOREIGN KEY (usuario_id)
        REFERENCES ocr_rag.ocr_usuario (id),
    CONSTRAINT fk_ocr_usuario_rol_rol FOREIGN KEY (rol_id)
        REFERENCES ocr_rag.ocr_rol (id)
);

COMMENT ON TABLE ocr_rag.ocr_usuario_rol IS 'Asignación de roles a usuarios (N:M).';

CREATE INDEX IF NOT EXISTS ix_ocr_usuario_rol_rol_id ON ocr_rag.ocr_usuario_rol (rol_id);

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_rol_permiso (
    rol_id      bigint NOT NULL,
    permiso_id  bigint NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  varchar(100),
    CONSTRAINT pk_ocr_rol_permiso PRIMARY KEY (rol_id, permiso_id),
    CONSTRAINT fk_ocr_rol_permiso_rol FOREIGN KEY (rol_id)
        REFERENCES ocr_rag.ocr_rol (id),
    CONSTRAINT fk_ocr_rol_permiso_permiso FOREIGN KEY (permiso_id)
        REFERENCES ocr_rag.ocr_permiso (id)
);

COMMENT ON TABLE ocr_rag.ocr_rol_permiso IS 'Asignación de permisos a roles (N:M).';

CREATE INDEX IF NOT EXISTS ix_ocr_rol_permiso_permiso_id ON ocr_rag.ocr_rol_permiso (permiso_id);

-- =====================================================================================
-- Refresh tokens (rotativos; el valor se guarda siempre hasheado)
-- =====================================================================================

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_refresh_token (
    id           bigint GENERATED ALWAYS AS IDENTITY,
    usuario_id   bigint NOT NULL,
    token_hash   text NOT NULL,
    expires_at   timestamptz NOT NULL,
    revoked_at   timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now(),
    created_by   varchar(100),
    CONSTRAINT pk_ocr_refresh_token PRIMARY KEY (id),
    CONSTRAINT uq_ocr_refresh_token_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_ocr_refresh_token_usuario FOREIGN KEY (usuario_id)
        REFERENCES ocr_rag.ocr_usuario (id)
);

COMMENT ON TABLE ocr_rag.ocr_refresh_token IS 'Refresh tokens rotativos emitidos por login; se guardan hasheados, nunca en texto plano.';
COMMENT ON COLUMN ocr_rag.ocr_refresh_token.token_hash IS 'Hash del refresh token (nunca el valor real).';
COMMENT ON COLUMN ocr_rag.ocr_refresh_token.revoked_at IS 'Momento de revocación (rotación o logout); NULL si sigue vigente.';

CREATE INDEX IF NOT EXISTS ix_ocr_refresh_token_usuario_id ON ocr_rag.ocr_refresh_token (usuario_id);

-- =====================================================================================
-- Documentos y chunks (OCR + RAG sobre pgvector)
-- =====================================================================================

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_documento (
    id               bigint GENERATED ALWAYS AS IDENTITY,
    nombre_archivo   varchar(300) NOT NULL,
    estado           varchar(30) NOT NULL DEFAULT 'pendiente',
    idioma           varchar(20),
    paginas          integer,
    error_detalle    text,
    creado_por_id    bigint NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    created_by       varchar(100),
    updated_at       timestamptz,
    updated_by       varchar(100),
    CONSTRAINT pk_ocr_documento PRIMARY KEY (id),
    CONSTRAINT fk_ocr_documento_usuario FOREIGN KEY (creado_por_id)
        REFERENCES ocr_rag.ocr_usuario (id),
    CONSTRAINT ck_ocr_documento_estado
        CHECK (estado IN ('pendiente', 'procesando', 'procesado', 'error'))
);

COMMENT ON TABLE ocr_rag.ocr_documento IS 'Documento subido para OCR y posterior indexación semántica.';
COMMENT ON COLUMN ocr_rag.ocr_documento.estado IS 'pendiente | procesando | procesado | error; lo actualiza el worker de OCR en background.';
COMMENT ON COLUMN ocr_rag.ocr_documento.error_detalle IS 'Detalle técnico si el OCR falló; no se expone tal cual al usuario final.';

CREATE INDEX IF NOT EXISTS ix_ocr_documento_creado_por_id ON ocr_rag.ocr_documento (creado_por_id);

CREATE TABLE IF NOT EXISTS ocr_rag.ocr_documento_chunk (
    id            bigint GENERATED ALWAYS AS IDENTITY,
    documento_id  bigint NOT NULL,
    orden         integer NOT NULL,
    contenido     text NOT NULL,
    embedding     vector(1536),
    created_at    timestamptz NOT NULL DEFAULT now(),
    created_by    varchar(100),
    CONSTRAINT pk_ocr_documento_chunk PRIMARY KEY (id),
    CONSTRAINT fk_ocr_documento_chunk_documento FOREIGN KEY (documento_id)
        REFERENCES ocr_rag.ocr_documento (id),
    CONSTRAINT uq_ocr_documento_chunk_documento_orden UNIQUE (documento_id, orden)
);

COMMENT ON TABLE ocr_rag.ocr_documento_chunk IS 'Fragmentos de texto de un documento, con su embedding para búsqueda semántica.';
COMMENT ON COLUMN ocr_rag.ocr_documento_chunk.orden IS 'Posición del fragmento dentro del documento, para reconstruir el orden original.';
COMMENT ON COLUMN ocr_rag.ocr_documento_chunk.embedding IS 'Embedding de "contenido" generado con text-embedding-3-small (1536 dimensiones).';

-- Índice para búsqueda por similitud coseno (el usado por text-embedding-3-small).
CREATE INDEX IF NOT EXISTS ix_ocr_documento_chunk_embedding_hnsw
    ON ocr_rag.ocr_documento_chunk
    USING hnsw (embedding vector_cosine_ops);

COMMIT;
