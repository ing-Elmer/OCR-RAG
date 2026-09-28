# CLAUDE.md

Este proyecto sigue el **estándar de desarrollo** (agentes, reglas y comandos en `.claude/`).
Las reglas generales viven en `.claude/rules/`; acá solo va lo propio de este sistema.

## Perfil del proyecto

| Clave | Valor |
|---|---|
| Nombre del sistema | OCR-RAG |
| Paquete Python (`<app>`) | `ocr_rag` → `backend/src/ocr_rag/{api,application,core,infrastructure}`, tests en `backend/tests/` |
| Versión de Python | `3.13` (fijada en `backend/.python-version`) |
| Ruta backend | `backend/` (`backend/pyproject.toml`) |
| Ruta frontend | `frontend/` |
| Ruta scripts SQL | `backend/db/` |
| Schema PostgreSQL propio | `ocr_rag` |
| Versión de PostgreSQL | `16` con extensión `pgvector` — **TODO**: confirmar la versión que provisione Railway |
| Prefijo de tablas propias | `ocr_` |
| Rama base / de integración | `Develop` (con D mayúscula, así existe en el remoto) |
| Prefijo de tickets Jira | **TODO** — todavía no hay proyecto en Jira |
| Puerto API local | `8000` (`uv run uvicorn ocr_rag.api.main:app --loop asyncio:SelectorEventLoop`; el `--loop` es obligatorio en Windows porque psycopg async no funciona con el `ProactorEventLoop`, y es inocuo en Linux) |
| Puerto frontend local | `5173` |
| Health check | `GET /health` |
| Base local de desarrollo | `docker-compose.yml` (raíz) · `pgvector/pgvector:pg16` · `127.0.0.1:15432` (5432 y 5433 los usan dos PostgreSQL nativos de la máquina; en el DSN usar `127.0.0.1`, no `localhost`: en Windows `localhost` resuelve primero a IPv6 `::1` y el pool agota el timeout) · variables en `.env` raíz (ver `.env.example`) |

### Conexiones de datos (`ConnectionFactory`)
Los DSN/credenciales vienen de variables de entorno (ver `backend/.env.example`), nunca de este archivo.

| Nombre | Variable de entorno | Uso | Acceso |
|---|---|---|---|
| `MAIN` | `OCR_RAG_DB_MAIN_DSN` | Tablas propias del sistema y vectores (`pgvector`) | lectura/escritura |

### Roles y permisos
- Fuente de identidad: **propia** (tablas `ocr_usuario`, `ocr_rol`, `ocr_permiso` en el schema `ocr_rag`).
- Roles (seed en `backend/db/002_seed_roles_permisos.sql`):

  | Rol | `DOCUMENTOS_VER` | `DOCUMENTOS_CARGAR` | `CONSULTAS_REALIZAR` | `USUARIOS_ADMINISTRAR` |
  |---|---|---|---|---|
  | `ADMIN` | ✔ | ✔ | ✔ | ✔ |
  | `OPERADOR` | ✔ | ✔ | ✔ | |
  | `LECTOR` | ✔ | | ✔ | |

- Autenticación: JWT de acceso (`HS256`, 15 min, claim `type: "access"`) + refresh token opaco
  (7 días, guardado como hash SHA-256, rotado en cada uso; el reuso de uno revocado revoca toda
  la sesión del usuario). Endpoints `POST /api/auth/{login,refresh,logout}`.
- Primer administrador: `uv run python -m ocr_rag.cli crear-admin` (pide la contraseña por
  teclado; requiere haber ejecutado los scripts 001 y 002).
- El frontend resuelve rol y permisos desde `GET /api/me`, nunca desde los claims del JWT.

### Deploy
- Repositorio GitHub: `ing-Elmer/OCR-RAG` · CI: `.github/workflows/ci.yml` (checks `ci-backend`,
  `ci-frontend`) · rama que despliega: `Develop`.
- Backend: **Railway** · proyecto **TODO** · servicio **TODO** · URL **TODO** · base PostgreSQL de
  Railway **TODO** (necesita `pgvector`) · *Wait for CI* activado.
- Frontend: **Vercel** · proyecto **TODO** · dominio de producción **TODO** ·
  *Deployment Checks* `ci-backend` + `ci-frontend`.
- Variables del backend en Railway (solo nombres): `OCR_RAG_DB_MAIN_DSN` (referencia a
  `${{Postgres.DATABASE_URL}}`), `OCR_RAG_JWT_SIGNING_KEY`, `OCR_RAG_JWT_ALGORITHM`,
  `OCR_RAG_CORS_ORIGINS`, `OCR_RAG_OPENAI_API_KEY`, `OCR_RAG_OPENAI_CHAT_MODEL`,
  `OCR_RAG_OPENAI_EMBEDDING_MODEL`, `OCR_RAG_TESSERACT_LANGS`, `OCR_RAG_ENV`,
  `OCR_RAG_DOCS_ENABLED`.
- Variables del frontend en Vercel: `VITE_API_URL` (Production y Preview).

### Integraciones externas
- **Extracción de texto**: en los PDF se lee primero la capa de texto nativa (`pypdfium2`: parte
  muchas menos palabras que `pypdf`); solo las páginas sin texto se rasterizan (también
  `pypdfium2`, sin dependencias de sistema) y pasan por
  **Tesseract** (`pytesseract`, idiomas `spa`/`eng` instalados en la imagen). Las imágenes van
  directo a Tesseract. Todo es **bloqueante**: corre con `run_in_threadpool` dentro de la
  `BackgroundTaskQueue`, nunca en el request HTTP.
- **Tesseract no está instalado en Windows**: en desarrollo el backend corre en Docker Compose
  (servicio `backend`, misma imagen que Railway).
- **OpenAI** — generación de respuestas (chat) y embeddings (`text-embedding-3-small`, 1536
  dimensiones). API key como `SecretStr` en `Settings`.
- **pgvector** — los embeddings viven en `ocr_rag.ocr_documento_chunk.embedding` en la misma
  base PostgreSQL, no en un vector store aparte.

### Corpus normativo
- Manifiesto empaquetado: `backend/src/ocr_rag/cli/corpus/normativa_centroamerica.toml`
  (CAUCA IV, RECAUCA IV y Convenio Arancelario). Carga:
  `docker compose exec backend python -m ocr_rag.cli cargar-corpus --usuario <u> [--dry-run]`.
  Es idempotente por SHA-256 y guarda `fuente_url`. Cambiar el manifiesto requiere
  reconstruir la imagen.
- **Antes de sumar una fuente, verificar su contenido página por página** (qué resolución y qué
  rango de artículos trae), no solo el título. La edición de la Imprenta Nacional de CR se
  presentaba como "CAUCA y RECAUCA" y en realidad mezclaba el CAUCA III derogado con el
  reglamento viejo (Res. 101-2002). El RAG terminó citando artículos derogados.
- Los textos de FAOLEX son las versiones originales de 2008 y **no incluyen reformas
  posteriores**. Pendiente: sumar las resoluciones modificatorias vigentes.

### Evaluación del RAG
- Set: `backend/src/ocr_rag/cli/evaluacion/normativa_ca.toml`. Son 16 casos y 27 artículos
  esperados, verificados contra el texto de CAUCA IV y RECAUCA IV.
- Correr: `docker compose exec backend python -m ocr_rag.cli evaluar --usuario <u> [--salida-json /tmp/e.json]`.
  Hace consultas reales a OpenAI (unos centavos). Desde Git Bash, anteponer
  `MSYS_NO_PATHCONV=1` para que `/tmp` no se convierta en ruta de Windows.
- **Correr la evaluación antes y después de cualquier cambio** de prompt, chunking, búsqueda o
  modelo, y comparar contra la línea base:

  | Fecha | Cambio | hit@k | MRR | Citas completas |
  |---|---|---|---|---|
  | 2026-09-27 | Fase 1 (híbrida + artículos + prompt con ejemplo de cita) | 1.00 | 0.79 | 81% |

- Las respuestas varían entre corridas (temperature 0.1): una diferencia de ±1 caso no es
  significativa. Antes de culpar al modelo, mirar el JSON: la métrica también puede fallar
  (pasó con "CAUCA" vs. "CAUCA IV").
- Pendiente: sumar casos negativos (preguntas sin respuesta en el corpus) para medir si el
  sistema inventa.

### Integración con Codex
Codex CLI (≥ 0.157) se usa desde Claude en modo no interactivo. Ya no expone un servidor MCP
(`codex mcp-server` no existe en esa versión), así que no se integra por MCP.
- `/codex-revisar [rama base]` — segunda opinión: `codex exec -s read-only` (no `codex review`, que no acepta instrucciones con `--uncommitted`/`--base`); Claude
  verifica cada hallazgo en el código y los consolida con su propia revisión.
- `/codex-delegar <tarea>` — Claude arma un prompt autosuficiente (perfil + reglas + contrato +
  límites) y lo ejecuta con `codex exec -s workspace-write`. Después verifica el resultado con
  build, tests y reglas, igual que con un subagente.
- Codex **no** lee `CLAUDE.md` ni `.claude/rules/` por su cuenta (no hay `AGENTS.md`). Por eso
  el contexto viaja siempre dentro del prompt.
- Límites iguales a los del estándar: sin SQL, sin secretos, sin commit/push y nunca
  `danger-full-access`.

## Dominio
Sistema de **OCR + RAG**: se suben documentos (PDF o imagen), se les extrae el texto con
Tesseract, se parten en chunks, se generan embeddings con OpenAI y se guardan en `pgvector`.
Sobre ese corpus se responden consultas en lenguaje natural recuperando los chunks más
relevantes y pasándoselos al modelo de chat.

## Excepciones al estándar
- **Rama base `Develop`** (con mayúscula) en lugar de `develop`: es el nombre que ya existe en el
  remoto. Los workflows y la protección de rama usan esa grafía exacta.
- **Archivos subidos como `bytea` en PostgreSQL** (tabla `ocr_documento_archivo`), no en disco
  ni en un bucket: el contenedor de Railway es efímero y así no hace falta otro servicio.
  Máximo `OCR_RAG_MAX_UPLOAD_MB` (20 MB por defecto). Los listados nunca leen el `bytea`.

## Deuda técnica conocida
Proyecto nuevo: el esqueleto se creó alineado al estándar. Lo que falta todavía no es deuda
sino alcance pendiente:

- **Sin límite de intentos de login** (rate limiting / bloqueo tras fallos): pendiente.
- **Scripts SQL por ambiente**: base local con `001` a `011` ejecutados. En Railway, ninguno
  todavía.
- **Deploy sin configurar**: Railway y Vercel todavía no existen (ver TODO en la sección Deploy).
- **`gh` no está instalado** en la máquina local, así que `/pr` no puede crear el PR desde acá.
- **Antivirus que intercepta HTTPS (Avast Web Shield)**: en la máquina de desarrollo, Avast
  re-firma las conexiones HTTPS con su propia raíz ("Avast Web/Mail Shield Root"). Windows
  confía en ella, pero `uv` no (hay que usar `uv sync --system-certs`) y los contenedores Linux
  tampoco, así que `docker compose build` falla con `UnknownIssuer` al descargar de PyPI.
  Solución: excluir `pypi.org` y `files.pythonhosted.org` del *HTTPS scanning* de Avast, o
  desactivar esa opción. No es un problema del proyecto: el CI de GitHub Actions no lo tiene.
  (Antes se lo había diagnosticado como "proxy corporativo": era Avast.)
- **`agent-view.vsix`** quedó versionado en la raíz desde el commit inicial del kit; evaluar si
  corresponde sacarlo del repo.
