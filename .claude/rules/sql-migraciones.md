---
paths:
  - "**/*.sql"
---

# Scripts SQL (PostgreSQL)

Carpeta de scripts: la que indica el perfil del proyecto.

- Nombre: `NNN_<verbo>_<descripcion>.sql` con `NNN` de 3 dígitos y verbo `create`, `alter`,
  `seed`, `update` o `drop`.
- **Números únicos**: antes de crear un script, listar la carpeta y usar el siguiente número
  libre. Nunca dos scripts con el mismo número, aunque sean de ramas distintas; si hay conflicto
  al integrar, se renumera el más nuevo.
- Schema explícito en cada objeto (`<schema>.<prefijo>_…`). Tablas y columnas en
  **snake_case minúscula** y sin comillas dobles.
- Claves primarias `bigint GENERATED ALWAYS AS IDENTITY` (o `uuid` si el perfil lo indica);
  fechas en `timestamptz`; textos en `text`/`varchar(n)`; montos en `numeric(p,s)`, nunca
  `float`.
- Constraints e índices con nombre: `pk_`, `fk_`, `uq_`, `ck_`, `ix_`. Nunca nombres
  autogenerados. Toda FK lleva su índice.
- Columnas de auditoría en tablas transaccionales: `created_at`, `created_by`, `updated_at`,
  `updated_by`.
- Idempotentes: `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`,
  `CREATE INDEX IF NOT EXISTS`; para constraints, bloque `DO $$ … $$` que chequea
  `pg_constraint`.
- Cada script envuelto en `BEGIN; … COMMIT;` (DDL transaccional). Índices sobre tablas grandes
  en producción: `CREATE INDEX CONCURRENTLY` en un script aparte, sin transacción.
- Documentar tablas y columnas nuevas con `COMMENT ON`.
- Un script = un cambio lógico. Los datos de prueba van en scripts `seed_` separados, nunca
  mezclados con DDL.
- Nunca DML contra conexiones o schemas marcados como solo lectura en el perfil.
- **No ejecutar** scripts (ni con `psql`): escribirlos y pedir al usuario que los corra o lo
  confirme.
