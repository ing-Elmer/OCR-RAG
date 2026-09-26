-- 002_seed_roles_permisos.sql
-- Carga el catálogo inicial de permisos y roles, y asigna los permisos a cada rol.
-- Idempotente: puede correrse más de una vez sin duplicar filas ni fallar.
-- Requiere que 001_create_schema_inicial.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

-- =====================================================================================
-- Permisos
-- =====================================================================================

INSERT INTO ocr_rag.ocr_permiso (codigo, nombre) VALUES
    ('DOCUMENTOS_VER', 'Ver documentos'),
    ('DOCUMENTOS_CARGAR', 'Cargar documentos'),
    ('CONSULTAS_REALIZAR', 'Realizar consultas (RAG)'),
    ('USUARIOS_ADMINISTRAR', 'Administrar usuarios')
ON CONFLICT (codigo) DO NOTHING;

-- =====================================================================================
-- Roles
-- =====================================================================================

INSERT INTO ocr_rag.ocr_rol (codigo, nombre) VALUES
    ('ADMIN', 'Administrador'),
    ('OPERADOR', 'Operador'),
    ('LECTOR', 'Lector')
ON CONFLICT (codigo) DO NOTHING;

-- =====================================================================================
-- Asignación de permisos a roles
-- =====================================================================================

-- ADMIN: los 4 permisos.
INSERT INTO ocr_rag.ocr_rol_permiso (rol_id, permiso_id)
SELECT r.id, p.id
  FROM ocr_rag.ocr_rol r
  JOIN ocr_rag.ocr_permiso p
    ON p.codigo IN ('DOCUMENTOS_VER', 'DOCUMENTOS_CARGAR', 'CONSULTAS_REALIZAR', 'USUARIOS_ADMINISTRAR')
 WHERE r.codigo = 'ADMIN'
ON CONFLICT (rol_id, permiso_id) DO NOTHING;

-- OPERADOR: ver, cargar y consultar (sin administrar usuarios).
INSERT INTO ocr_rag.ocr_rol_permiso (rol_id, permiso_id)
SELECT r.id, p.id
  FROM ocr_rag.ocr_rol r
  JOIN ocr_rag.ocr_permiso p
    ON p.codigo IN ('DOCUMENTOS_VER', 'DOCUMENTOS_CARGAR', 'CONSULTAS_REALIZAR')
 WHERE r.codigo = 'OPERADOR'
ON CONFLICT (rol_id, permiso_id) DO NOTHING;

-- LECTOR: solo ver y consultar.
INSERT INTO ocr_rag.ocr_rol_permiso (rol_id, permiso_id)
SELECT r.id, p.id
  FROM ocr_rag.ocr_rol r
  JOIN ocr_rag.ocr_permiso p
    ON p.codigo IN ('DOCUMENTOS_VER', 'CONSULTAS_REALIZAR')
 WHERE r.codigo = 'LECTOR'
ON CONFLICT (rol_id, permiso_id) DO NOTHING;

COMMIT;
