-- 011_alter_documento_control_procesamiento.sql
-- Agrega a "ocr_documento" el control de concurrencia del procesamiento OCR + embeddings:
-- "version_procesamiento" (bloqueo optimista: el worker solo guarda un resultado si la versión
-- que tomó sigue siendo la vigente) y "clasificacion_pendiente" (si la clasificación automática
-- del tipo de documento sigue pendiente, en lugar de vivir solo en el closure de la tarea
-- encolada, que se pierde en un reinicio).
-- Idempotente: puede correrse más de una vez sin fallar.
-- Requiere que 007_alter_documento_tipo_norma.sql ya se haya ejecutado.
-- NO ejecutar este script automáticamente: lo corre una persona contra el ambiente, a mano.

BEGIN;

ALTER TABLE ocr_rag.ocr_documento
    ADD COLUMN IF NOT EXISTS clasificacion_pendiente boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS version_procesamiento integer NOT NULL DEFAULT 0;

COMMENT ON COLUMN ocr_rag.ocr_documento.clasificacion_pendiente IS
    'Si la carga no indicó tipoDocumento, queda en true hasta que el worker la clasifique '
    'automáticamente (o una edición manual del tipo la limpie primero). Se lee siempre de la '
    'base al tomar el documento para procesar, nunca de un parámetro en memoria: así sobrevive '
    'a un reinicio del proceso.';
COMMENT ON COLUMN ocr_rag.ocr_documento.version_procesamiento IS
    'Contador de bloqueo optimista del procesamiento OCR + embeddings. El worker toma el '
    'documento junto con esta versión y solo guarda su resultado (o marca error) si sigue '
    'vigente; si cambió mientras procesaba (un reprocesamiento más nuevo ya se encoló, por '
    'ejemplo por un PATCH que cambió el tipo), descarta el resultado sin tocar el estado.';

COMMIT;
