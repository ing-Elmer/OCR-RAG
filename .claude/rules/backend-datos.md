---
paths:
  - "**/infrastructure/**/*.py"
  - "**/repositories/**/*.py"
---

# Backend — acceso a datos (psycopg 3 + PostgreSQL)

- SQL escrito a mano, async, mapeado directo al DTO de Core con `class_row`:
  ```python
  async def listar(self, activo: bool, limite: int, offset: int) -> list[FeatureResponse]:
      sql = """
          SELECT f.id, f.nombre, f.created_at
            FROM <schema>.<prefijo>_feature f
           WHERE f.activo = %(activo)s
           ORDER BY f.id
           LIMIT %(limite)s OFFSET %(offset)s
      """
      async with self._db.connection("<NOMBRE>") as conn:
          async with conn.cursor(row_factory=class_row(FeatureResponse)) as cur:
              await cur.execute(sql, {"activo": activo, "limite": limite, "offset": offset})
              return await cur.fetchall()
  ```
- SQL siempre parametrizado con placeholders nombrados `%(nombre)s`; **nunca** f-strings,
  `%`/`.format()` ni concatenación con input. Identificadores dinámicos (orden por columna)
  solo desde una lista blanca y con `psycopg.sql.Identifier`.
- Tablas y columnas en **snake_case minúscula** sin comillas, con schema explícito
  (`<schema>.<prefijo>_tabla`). Placeholders en `snake_case`.
- Conexiones **solo** vía `ConnectionFactory.connection("<NOMBRE>")` (un `AsyncConnectionPool`
  por nombre, creado en el `lifespan`), con los nombres que declara el perfil del proyecto.
  Las conexiones marcadas **solo lectura** en el perfil se abren con
  `default_transaction_read_only=on` y nunca reciben INSERT/UPDATE/DELETE.
- Timeout por sentencia configurado en el pool (`statement_timeout`), nunca queries sin límite.
- Operaciones que escriben en varias tablas van en una transacción explícita
  (`async with conn.transaction():`) dentro del mismo método del repositorio.
- `INSERT`/`UPDATE` que necesiten el registro resultante usan `RETURNING`, no un `SELECT` extra.
- Los repositorios no loguean, no tienen lógica de negocio ni valores por defecto: devuelven lo
  que hay en la base. Cada repositorio implementa el `Protocol` declarado en
  `core/repositories.py`.
- Listados paginados en la base (`LIMIT … OFFSET …`, o keyset si la tabla es grande), nunca
  traer todo y paginar en memoria.

## Datos de sistemas externos
- Cuando un código de un sistema externo representa el mismo concepto que un catálogo propio,
  se agrega una columna de mapeo (`<sistema>_code`) a la tabla de catálogo propia existente.
  Nunca hardcodear el mapeo en Python ni crear una tabla paralela: el mapeo debe poder
  corregirse con un `UPDATE`, sin redeploy.
