---
paths:
  - "**/.github/**"
  - "**/railway.toml"
  - "**/railway.json"
  - "**/vercel.json"
  - "**/Dockerfile"
---

# GitHub, GitHub Actions y despliegue (Railway + Vercel)

Plantillas base en `.claude/templates/proyecto/` (las copia `/adoptar`). Repositorio, rama base,
servicios y dominios: los que declara el perfil del proyecto.

## Modelo
- **GitHub Actions hace CI, no deploy.** Railway (backend) y Vercel (frontend) despliegan con
  su integración nativa de GitHub y **esperan al CI**:
  - Railway: *Wait for CI* activado en el servicio (requiere que `ci.yml` corra en `push` a la
    rama que despliega).
  - Vercel: *Deployment Checks* con los checks `ci-backend` y `ci-frontend` requeridos.
- Así no se guardan tokens de Railway ni de Vercel en GitHub. Agregar un `deploy.yml` con
  `RAILWAY_TOKEN`/`VERCEL_TOKEN` es una excepción que se declara en el perfil.
- A la rama base solo se llega por PR con CI en verde (protección de rama).

## `ci.yml`
- Dos jobs con nombre fijo **`ci-backend`** y **`ci-frontend`**: son los nombres que exigen la
  protección de rama, Railway y Vercel. Renombrarlos obliga a actualizar esos tres lugares, y
  ningún otro workflow puede usar esos nombres.
- Mismos pasos que `/verificar`: backend `uv sync --frozen` → `ruff check` →
  `ruff format --check` → `mypy` → `lint-imports` → `pytest`; frontend `npm ci` →
  `npm run build` → `npm run test`. Si cambian en un lado, cambian en el otro.
- Sin filtros `paths` a nivel de workflow: un check requerido que no corre deja el PR bloqueado.
- Tests que necesiten base usan `services: postgres` efímero del job, nunca la base de Railway.

## Seguridad de los workflows
- `permissions:` explícito con lo mínimo (`contents: read`); un job pide más solo si lo necesita.
- `actions/*` por tag mayor; actions de terceros por **SHA completo** con la versión en un
  comentario (`uses: owner/action@<sha> # v1.2.3`). Dependabot las mantiene al día.
- `actions/checkout` con `persist-credentials: false`.
- Secretos solo en GitHub Secrets (mejor por *environment*); nunca en el YAML ni impresos.
- Prohibido `pull_request_target` que haga checkout del código del PR, e interpolar
  `${{ github.event.* }}` directo en `run:` (pasarlo por `env:`).
- `concurrency` por rama con `cancel-in-progress: true`; `timeout-minutes` en cada job.

## Railway (backend)
- Build con el `Dockerfile` del backend (multi-stage, `uv sync --frozen --no-dev`, usuario no
  root, `uvicorn` escuchando en `$PORT` con `--proxy-headers`).
- `railway.toml` en `backend/`, y en el servicio: *Root Directory* `/backend` y
  *Config-as-code* `/backend/railway.toml` (Railway no lo busca dentro del Root Directory).
- `healthcheckPath = "/health"`: un deploy que no pasa el health check no recibe tráfico.
- Variables del servicio: las de `backend/.env.example`. La conexión a PostgreSQL de Railway se
  carga como **variable de referencia** (`<APP>_DB_<NOMBRE>_DSN = ${{Postgres.DATABASE_URL}}`),
  nunca copiando el valor.
- Sin `preDeployCommand` de migraciones: los scripts SQL los ejecuta una persona contra la base
  del ambiente, antes del merge que los necesita.

## Vercel (frontend)
- *Root Directory* `frontend`; `vercel.json` con `framework: vite`, `npm ci`, rewrite de SPA a
  `index.html`, cache inmutable en `/assets/*` y headers de seguridad.
- `VITE_API_URL` por ambiente (Production → API de producción, Preview → API de
  staging/desarrollo). Solo valores públicos: todo `VITE_*` termina en el bundle.
- CORS del backend: el dominio de producción de Vercel va en los orígenes explícitos. Los
  previews (`*.vercel.app`) se habilitan solo en el backend que no es de producción.

## Repositorio
- `.github/dependabot.yml` (`uv`, `npm`, `github-actions`, semanal y agrupado),
  `.github/CODEOWNERS` y `.github/pull_request_template.md`.
- Protección de rama, environments, *Wait for CI* y *Deployment Checks* se configuran a mano en
  cada plataforma: Claude los documenta y verifica, no los cambia.
