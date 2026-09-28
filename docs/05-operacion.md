# 05 · Operación

Guía para levantar el sistema en una máquina de desarrollo y operarlo. Los valores exactos
(puertos, nombres de variables) salen del perfil en [`CLAUDE.md`](../CLAUDE.md).

## Requisitos

- Docker Desktop.
- Python 3.13 con `uv`, y Node 24 con npm. Solo hacen falta para desarrollar y correr los tests;
  el backend corre en Docker.
- Una API key de OpenAI con saldo.

## Configuración (una vez)

Los archivos `.env` **no se versionan**. Cada uno se crea copiando su `.env.example`:

| Archivo | Variables obligatorias |
|---|---|
| `.env` (raíz, lo usa Docker Compose) | `OCR_RAG_PG_PASSWORD` |
| `backend/.env` | `OCR_RAG_DB_MAIN_DSN`, `OCR_RAG_JWT_SIGNING_KEY`, `OCR_RAG_OPENAI_API_KEY` |
| `frontend/.env` | `VITE_API_URL=http://localhost:8000` |

En `backend/.env`, el DSN apunta a `127.0.0.1:15432`, **no** a `localhost` (ver problemas
conocidos). Dentro de Docker Compose el backend usa el servicio `postgres` automáticamente.

## Levantar el entorno

```
docker compose up -d --build       # base + backend (Tesseract incluido)
cd frontend && npm run dev          # frontend en http://localhost:5173
```

Para trabajar en el backend sin Docker:
`uv run uvicorn ocr_rag.api.main:app --loop asyncio:SelectorEventLoop`, desde `backend/`.

## Scripts SQL

Los ejecuta **una persona**, en orden, contra la base de cada ambiente. La aplicación nunca los
corre sola. En local:

```
docker compose exec postgres psql -U ocr_rag -d ocr_rag -f /scripts/<script>.sql
```

| # | Script | Qué hace |
|---|---|---|
| 001 | `create_schema_inicial` | Schema, pgvector, usuarios, roles, documentos, fragmentos |
| 002 | `seed_roles_permisos` | Roles ADMIN, OPERADOR, LECTOR y sus permisos |
| 003 | `create_documento_archivo` | Archivos originales (`bytea`) |
| 004 | `alter_documento_chunk_pagina` | Página de cada fragmento |
| 005 | `alter_documento_fuente_url` | URL de origen del corpus |
| 006 | `create_ix_documento_archivo_sha256` | Índice para detectar duplicados |
| 007 | `alter_documento_tipo_norma` | Tipo de documento y norma |
| 008 | `create_ix_documento_tipo_documento` | Índice por tipo |
| 009 | `alter_documento_chunk_articulo_tsv` | Artículo y texto completo de cada fragmento |
| 010 | `create_ix_documento_chunk_contenido_tsv` | Índice GIN de texto completo |
| 011 | `alter_documento_control_procesamiento` | Versión y clasificación pendiente |

Estado: en la **base local** están ejecutados del 001 al 011. En **Railway**, ninguno todavía.

## Comandos de operación (CLI)

Se ejecutan dentro del contenedor: `docker compose exec backend python -m ocr_rag.cli <comando>`.

| Comando | Para qué |
|---|---|
| `crear-admin` | Crea el primer usuario ADMIN. Pide la contraseña por teclado (mínimo 12 caracteres) |
| `cargar-corpus --usuario <u> [--dry-run] [--solo <id>]` | Descarga y carga las normas del manifiesto. Omite las ya cargadas. `--dry-run` no escribe ni gasta en OpenAI |
| `reprocesar (--todos \| --id N[,N…])` | Vuelve a extraer, fragmentar y generar embeddings. Hace falta después de cambiar el chunking o la limpieza |
| `evaluar --usuario <u> [--salida-json <ruta>]` | Corre el set de evaluación con consultas reales. Ver [04](04-corpus-y-evaluacion.md) |

Desde Git Bash, anteponer `MSYS_NO_PATHCONV=1` a los comandos que llevan rutas como `/tmp/...`.

## Verificación (lo mismo que corre el CI)

| Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|
| `uv run ruff check` | `npm ci` |
| `uv run ruff format --check` | `npm run build` |
| `uv run mypy` | `npm run test` |
| `uv run lint-imports` | |
| `uv run pytest` | |

Estado actual: backend **309 tests** y frontend **53 tests**, todo en verde.

## Problemas conocidos del entorno de desarrollo

| Síntoma | Causa | Solución |
|---|---|---|
| `uv sync` o `docker compose build` fallan con `invalid peer certificate: UnknownIssuer` | **Avast** intercepta HTTPS con su propio certificado; los contenedores Linux y `uv` no confían en él | Excluir `pypi.org` y `files.pythonhosted.org` del escaneo HTTPS de Avast, o usar `uv sync --system-certs` |
| El backend fuera de Docker no conecta a la base y agota el pool | En Windows, `localhost` resuelve primero a IPv6 `::1` y el contenedor escucha en IPv4 | Usar `127.0.0.1` en el DSN |
| `Psycopg cannot use the 'ProactorEventLoop'` | psycopg async no funciona con el event loop por defecto de Windows | `--loop asyncio:SelectorEventLoop` en uvicorn |
| Puertos 5432 y 5433 ocupados | Hay dos PostgreSQL instalados en Windows | Docker Compose usa el 15432 |
| El frontend dice "No se pudo conectar con el servidor" | Falta `frontend/.env` (`VITE_API_URL`) | Crearlo y reiniciar `npm run dev` |

## Despliegue

Checklist para el primer despliegue. Todavía no se hizo; está bloqueado por la facturación de
GitHub.

1. **GitHub:** proteger `Develop`, con PR obligatorio y los checks `ci-backend` y `ci-frontend`
   requeridos.
2. **Railway:**
   - servicio conectado al repo, con Root Directory `/backend` y Config-as-code
     `/backend/railway.toml`;
   - *Wait for CI* activado;
   - base PostgreSQL con **pgvector**;
   - variables `OCR_RAG_*`, con el DSN como referencia a `${{Postgres.DATABASE_URL}}`.
3. **Base de Railway:** ejecutar los scripts 001 a 011 y después
   `cargar-corpus --usuario <admin>`.
4. **Vercel:** Root Directory `frontend`, `VITE_API_URL` por ambiente y *Deployment Checks* con
   los dos checks.
5. **CORS:** agregar el dominio de Vercel a `OCR_RAG_CORS_ORIGINS`.
