# CLAUDE.md

Este proyecto sigue el **estándar de desarrollo** (agentes, reglas y comandos en `.claude/`).
Las reglas generales viven en `.claude/rules/`; acá solo va lo propio de este sistema.

## Perfil del proyecto

| Clave | Valor |
|---|---|
| Nombre del sistema | `<Nombre legible>` |
| Paquete Python (`<app>`) | `<app>` → `backend/src/<app>/{api,application,core,infrastructure}`, tests en `backend/tests/` |
| Versión de Python | `<3.13>` (fijada en `backend/.python-version`) |
| Ruta backend | `backend/` (`backend/pyproject.toml`) |
| Ruta frontend | `frontend/` |
| Ruta scripts SQL | `backend/db/` |
| Schema PostgreSQL propio | `<schema>` |
| Versión de PostgreSQL | `<16>` |
| Prefijo de tablas propias | `<prefijo>_` |
| Rama base / de integración | `develop` |
| Prefijo de tickets Jira | `<PROY>-` |
| Puerto API local | `<puerto>` (`uv run uvicorn <app>.api.main:app`) |
| Puerto frontend local | `5173` |
| Health check | `GET /health` |

### Conexiones de datos (`ConnectionFactory`)
Los DSN/credenciales vienen de variables de entorno (ver `backend/.env.example`), nunca de este archivo.

| Nombre | Variable de entorno | Uso | Acceso |
|---|---|---|---|
| `<CONEXION_PROPIA>` | `<APP>_DB_<NOMBRE>_DSN` | Tablas propias del sistema | lectura/escritura |
| `<CONEXION_EXTERNA>` | `<APP>_DB_<NOMBRE>_DSN` | Sistema externo `<nombre>` | **solo lectura** |

### Roles y permisos
- Fuente de identidad: `<propia | sincronizada desde otro sistema>`.
- Roles: `<ROL_1>`, `<ROL_2>`, …

### Deploy
- Repositorio GitHub: `<org>/<repo>` · CI: `.github/workflows/ci.yml` (checks `ci-backend`,
  `ci-frontend`) · rama que despliega: `<main>`.
- Backend: **Railway** · proyecto `<nombre>` · servicio `<nombre>` · URL `<https://…up.railway.app>`
  · base PostgreSQL de Railway `<servicio Postgres>` · *Wait for CI* activado.
- Frontend: **Vercel** · proyecto `<nombre>` · dominio de producción `<https://…>` ·
  *Deployment Checks* `ci-backend` + `ci-frontend`.
- Variables del backend en Railway (solo nombres): `<APP>_DB_<NOMBRE>_DSN` (referencia a
  `${{Postgres.DATABASE_URL}}`), `<APP>_JWT_SIGNING_KEY`, `<APP>_CORS_ORIGINS`, …
- Variables del frontend en Vercel: `VITE_API_URL` (Production y Preview).

### Integraciones externas
- `<AWS S3 / Textract / Bedrock / SMTP / …>` — qué se usa y para qué.

## Dominio
Breve descripción del negocio, actores y flujo principal (o link a `docs/`).

## Excepciones al estándar
Lo que este proyecto hace distinto al estándar y por qué (vacío si no hay).

## Deuda técnica conocida
Lista viva de lo que no cumple el estándar todavía.
