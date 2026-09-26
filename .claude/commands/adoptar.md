---
description: Adopta el estándar en el proyecto actual — completa el perfil del proyecto y reporta diferencias con el estándar
argument-hint: [nuevo]  (vacío = proyecto existente; "nuevo" = proyecto desde cero)
---

Adoptá el estándar de desarrollo en este proyecto. Modo: **$ARGUMENTS** (vacío = proyecto existente).

## 1. Perfil del proyecto
- Si el `CLAUDE.md` raíz no tiene `## Perfil del proyecto`, crealo a partir de
  `.claude/templates/CLAUDE.proyecto.md`.
- **Proyecto existente:** inferí cada valor del código (`pyproject.toml`, `.python-version`,
  nombre del paquete en `src/`, `core/settings.py` (solo **nombres** de variables y conexiones,
  **nunca** valores; no leas `.env`), comando de arranque/`Dockerfile`, `vite.config.ts`,
  `.github/workflows/*.yml`, remoto de git (`git remote -v`) y ramas, carpeta de scripts SQL).
- **Proyecto nuevo:** preguntame los datos que no se puedan inferir (nombre, paquete `<app>`,
  schema, prefijo de tablas, conexiones, prefijo Jira, puertos).
- Marcá con `TODO` lo que no se pudo determinar. Mostrame el perfil y esperá mi OK antes de
  guardarlo.

## 2. Diagnóstico contra el estándar (solo proyecto existente)
Revisá el código contra `.claude/rules/` y armá una tabla: regla · cumple (sí / parcial / no) ·
evidencia (`archivo:línea`) · esfuerzo para alinearlo (bajo / medio / alto). Prioridad especial a:
secretos versionados, `.gitignore`, workflows sin `permissions:` o con actions sin fijar, `uv.lock` versionado, uso de ORM, SQL con f-strings,
contrato de capas (`import-linter`), `mypy --strict`, excepciones y `ApiResponse`,
`get_current_user`, tests de auth, piezas compartidas del frontend y números de scripts SQL
duplicados.

Volcá los incumplimientos en la sección `## Deuda técnica conocida` del `CLAUDE.md`.
**No corrijas código** en este comando.

## 3. Proyecto nuevo
Proponé el esqueleto y **esperá mi confirmación** antes de crear archivos:
- `backend/`: `pyproject.toml` (dependencias, `ruff`, `mypy --strict`, `pytest`, contrato
  `import-linter` de capas), `.python-version`, `.env.example`, `src/<app>/{api,application,core,infrastructure}`
  con `main.py` + `lifespan`, `ApiResponse`, `CamelModel`, `DomainError`, exception handlers,
  `ConnectionFactory`, `Settings`, `get_current_user`/`require_permission`, `GET /health`,
  `tests/` con `conftest.py`, y carpeta de scripts SQL.
- `frontend/` Vite con la estructura estándar.
- `.gitignore`.
- Copiá `.claude/templates/proyecto/` a la raíz (`.github/` con `ci.yml`, `dependabot.yml`,
  `CODEOWNERS` y plantilla de PR; `backend/Dockerfile`, `.dockerignore` y `railway.toml`;
  `frontend/vercel.json` y `.nvmrc`), reemplazando los placeholders (`<app>`, rama base, rutas,
  versiones de Python/Node, equipos de CODEOWNERS) con el perfil. Seguí
  `.claude/rules/ci-github.md`.
- Al final, dame la **lista de configuración manual** (no la hagas vos):
  1. GitHub: protección de la rama base con PR obligatorio y checks `ci-backend` y
     `ci-frontend` requeridos.
  2. Railway: servicio conectado al repo, Root Directory `/backend`, Config-as-code
     `/backend/railway.toml`, *Wait for CI*, base PostgreSQL y variables (DSN como referencia).
  3. Vercel: proyecto con Root Directory `frontend`, `VITE_API_URL` por ambiente y
     *Deployment Checks* con los dos checks.
  4. CORS del backend con el dominio de Vercel.
  5. Ejecutar los scripts SQL iniciales contra la base de Railway (lo hace una persona).
