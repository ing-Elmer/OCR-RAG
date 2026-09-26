---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
---

# Backend — arquitectura en 4 capas (Python + FastAPI)

Stack: Python (versión fijada en `.python-version`), FastAPI, Pydantic v2, pydantic-settings,
psycopg 3 (async) + psycopg_pool, PostgreSQL, JWT propio (PyJWT) + bcrypt. Gestión con `uv`.
**Prohibido:** ORMs (SQLAlchemy ORM, SQLModel, Tortoise, Django ORM), query builders que
generen SQL, patrones tácticos de DDD (Entity / Value Object / Aggregate), estado mutable a nivel
de módulo (variables globales, singletons caseros).

Un único paquete `<app>` en `backend/src/<app>/` con cuatro subpaquetes:

| Capa | Contiene | Prohibido | Puede importar |
|---|---|---|---|
| `<app>.api` | `main.py` (app + lifespan), `routers/`, `dependencies.py` (armado de services), `errors.py` (exception handlers), `security.py` (usuario actual, permisos), modelos de formulario en `forms/` | Lógica de negocio, SQL | application, core |
| `<app>.application` | `services/`, `validators/` | SQL, `psycopg`, `fastapi` | core |
| `<app>.core` | `schemas/` (DTOs Pydantic), `repositories.py` (interfaces `Protocol`), `settings.py`, `exceptions.py` | I/O, `fastapi`, `psycopg` | — |
| `<app>.infrastructure` | `db.py` (`ConnectionFactory`), `repositories/`, clientes de servicios externos | Lógica de negocio, cálculos, valores por defecto, logging en repositorios | core |

- Las dependencias entre capas se validan con **`import-linter`** (contrato `layers` en
  `pyproject.toml`); romper el contrato rompe el build.
- Archivos y módulos en `snake_case`; clases en `PascalCase`.

## Services
- Clases comunes (sin FastAPI) que reciben por `__init__`: el repositorio (`<Feature>Repository`,
  tipado con el `Protocol` de Core), el validador y, si lo necesita, el `CurrentUser`.
  Logger: `logger = logging.getLogger(__name__)` a nivel de módulo.
- El armado (repositorio → validador → service) vive **solo** en `api/dependencies.py` como
  providers de `Depends`; los routers nunca instancian repositorios.
- DTOs en `core/schemas/<feature>.py`: `<Feature>Request` (entrada) y `<Feature>Response`
  (salida), heredando de `CamelModel` (ver `backend-api`).
- Validación en dos niveles:
  - **Forma** (tipos, largos, regex, rangos) → en el DTO Pydantic con `Field(...)`/validators.
  - **Negocio** (existencia, unicidad, reglas que miran la base) →
    `application/validators/<feature>_validator.py`, que el Service llama **antes de cualquier
    lógica** y que lanza `ValidationError(errors)` de Core. Nunca en el router.
- Todo I/O es `async`. Prohibido I/O bloqueante dentro de `async def`; si una librería es
  síncrona, `await run_in_threadpool(...)`.
- Tareas no bloqueantes (email, notificaciones, OCR, integraciones lentas) →
  `BackgroundTaskQueue` (sobre `asyncio.Queue`, worker iniciado en el `lifespan`), nunca dentro
  del request HTTP.
- Un flujo repetido en dos services (p. ej. login de dos tipos de usuario) se extrae a un
  componente compartido; no se duplica.

## Usuario actual
- Los claims se leen **solo** mediante la dependencia `get_current_user` de `api/security.py`,
  que devuelve un `CurrentUser` tipado (dataclass de Core).
- Prohibido decodificar el JWT o leer `request.headers["Authorization"]` / `request.state` en
  routers o services. Si un claim obligatorio falta, `get_current_user` lanza
  `UnauthorizedError` y el handler responde 401.

## Logging
- `logging` estándar → diagnóstico técnico (`warning` o superior en rutas de error conocidas),
  configurado una sola vez en el `lifespan`. Prohibido `print`.
- `SystemLogService` → auditoría de negocio persistente.
- No mezclar ambos. Nunca loguear passwords, tokens ni documentos completos.

## Configuración y herramientas
- `pyproject.toml` único en `backend/` + `uv.lock` versionado: una sola versión por paquete.
  Dependencias nuevas con `uv add` (pedir confirmación antes).
- `ruff` (lint + format) y `mypy --strict` sin errores; nada de `# type: ignore` sin código de
  error y comentario que lo justifique. Prohibido `Any` explícito en firmas públicas.
- Configuración tipada con `Settings(BaseSettings)` en `core/settings.py`, instanciada una vez
  al arrancar (falla rápido si falta un valor) y obtenida vía `Depends(get_settings)`. Nada de
  `os.environ[...]` / `os.getenv` sueltos en el código.
