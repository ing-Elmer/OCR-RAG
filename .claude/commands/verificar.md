---
description: Corre lint, tipos, capas y tests de backend y frontend, y reporta el resultado
argument-hint: [backend | frontend]  (vacío = ambos)
---

Verificá el proyecto. Alcance: **$ARGUMENTS** (si está vacío: backend y frontend).
Tomá las rutas del backend y del frontend del **perfil del proyecto**.

- Backend (en su carpeta, con `uv`):
  1. `uv sync --frozen` (si falla por el lock, avisame; no lo regeneres sin preguntar)
  2. `uv run ruff check` y `uv run ruff format --check`
  3. `uv run mypy`
  4. `uv run lint-imports` (contrato de capas)
  5. `uv run pytest`
- Frontend: `npm run build` (incluye `tsc`) y `npm run test`.

Reportá en una tabla: paso · resultado (OK / FALLA) · tests pasados/fallados · primer error
relevante. Si algo falla, analizá la causa pero **no la corrijas** sin preguntarme.
