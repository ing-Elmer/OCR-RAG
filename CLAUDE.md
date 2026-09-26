# CLAUDE.md — Estándar de desarrollo (kit de Claude Code)

Este repositorio define el **estándar** para construir sistemas nuevos con la misma arquitectura,
reglas y forma de trabajo. Nació de `aa_tts` (sistema de referencia, en .NET + Oracle) e incorpora
las mejoras que salieron de su deuda técnica; el backend del estándar migró después a
**Python + FastAPI + PostgreSQL** conservando la arquitectura en 4 capas, el envelope
`ApiResponse` y las reglas de datos. **No contiene nada específico de un sistema**: los datos
propios de cada proyecto (nombre, schema, conexiones, puertos, ticket, deploy) van en el
**perfil del proyecto** (ver abajo).

## Stack estándar
- **Backend:** Python · FastAPI · Pydantic v2 · psycopg 3 async con SQL a mano (nunca ORM) ·
  PostgreSQL · JWT propio (PyJWT) con refresh rotativo + bcrypt · `uv`, `ruff`, `mypy --strict`,
  `pytest`. Arquitectura en 4 capas dentro del paquete `<app>`:
  `api / application / core / infrastructure` (validada con `import-linter`).
- **Frontend:** React + TypeScript strict · Vite · Tailwind v4 · react-router v7 · axios · npm.
- **Repositorio y CI:** GitHub + GitHub Actions (CLI `gh`). **Deploy:** Railway (backend +
  PostgreSQL) y Vercel (frontend), con integración nativa que espera al CI. **Gestión:** Jira/Confluence
  (MCP `atlassian`).

## Perfil del proyecto (obligatorio en cada sistema)
Cada proyecto que adopta el estándar tiene en su `CLAUDE.md` raíz una sección
`## Perfil del proyecto` (plantilla en `.claude/templates/CLAUDE.proyecto.md`). Agentes, reglas y
comandos **leen ese perfil** para saber nombres, rutas, conexiones y puertos; nunca los asumen.
Si el perfil falta o está incompleto, pedile los datos al usuario o corré `/adoptar`.

## Estructura del kit
```
.mcp.json                  MCP compartidos: atlassian
.claude/settings.json      plugins, permisos, agente principal (orquestador)
.claude/settings.local.json MCP habilitados y rutas locales (personal, no se versiona)
.claude/agents/            orquestador, backend-python, frontend-react, qa
.claude/commands/          /adoptar, /jira, /feature-backend, /feature-frontend, /migracion,
                           /verificar, /revisar, /commit, /pr, /levantar, /qa
.claude/rules/             reglas del estándar; las que tienen `paths:` se cargan solo al tocar
                           esos archivos
  general.md               siempre activa: git, secretos, verificación, idioma, perfil
  backend-arquitectura.md  capas, services, validación, logging, usuario actual, herramientas
  backend-api.md           routers, ApiResponse, camelCase, excepciones, health check
  backend-datos.md         psycopg 3, SQL parametrizado, conexiones, convenciones PostgreSQL
  sql-migraciones.md       numeración única y convenciones de scripts PostgreSQL
  frontend-react.md        estructura de feature, API, auth, hooks compartidos
  frontend-estilos.md      Tailwind v4, componentes compartidos, accesibilidad
  testing.md               qué se testea obligatoriamente y cómo
  seguridad-config.md      secretos, Settings/.env, Docker, .gitignore
  ci-github.md             GitHub Actions, Railway, Vercel, dependabot, CODEOWNERS
.claude/skills/            frontend-design, react-best-practices, web-design-guidelines, webapp-testing
.claude/templates/         CLAUDE.proyecto.md (perfil del proyecto) y proyecto/ (archivos base de
                           .github/, Dockerfile, railway.toml, vercel.json que copia /adoptar)
```

## Cómo adoptar el estándar en un sistema
1. Copiar `.claude/` (sin `settings.local.json`) y `.mcp.json` a la raíz del proyecto.
2. Abrir Claude Code en el proyecto y correr `/adoptar`: completa el perfil del proyecto y
   reporta las diferencias entre el código existente y el estándar.

## Mantener el estándar
- Cualquier regla nueva debe ser **genérica**: si menciona un nombre, tabla, puerto o ruta de un
  sistema concreto, va al perfil de ese proyecto, no acá.
- Cuando una mejora se prueba en un proyecto, subila acá para que la hereden los demás.
- `aa_tts` (`C:\BitBukect\aa_tts`) queda como referencia de lectura para el dominio y el
  frontend; su backend es .NET + Oracle, así que **no** se copia su código de backend.
