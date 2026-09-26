---
description: Crea una feature backend completa en las 4 capas del estándar (DTOs, repositorio, service, validador, router, tests)
argument-hint: <NombreFeature> <descripción breve>
---

Creá la feature backend: **$ARGUMENTS**

Usá el agente `backend-python`. Tomá el paquete `<app>`, la ruta del backend, el schema, el
prefijo de tablas, la conexión y la carpeta de scripts del **perfil del proyecto**.

Piezas esperadas (dentro de `backend/src/<app>/`):
- **core:** `schemas/<feature>.py` con `<Feature>Request` y `<Feature>Response` (sobre
  `CamelModel`), el `Protocol` `<Feature>Repository` en `repositories.py` y, si aplica,
  excepciones de dominio que heredan de `DomainError` con su `status_code`.
- **infrastructure:** `repositories/<feature>_repository.py` (SQL a mano, `class_row`).
- **application:** `services/<feature>_service.py` y `validators/<feature>_validator.py`.
- **api:** `routers/<feature>.py` con `require_permission` y `ApiResponse[...]`, provider en
  `dependencies.py` y registro del router en `main.py`.
- **Tests:** `tests/application/test_<feature>_service.py` y `test_<feature>_validator.py`.
- **SQL:** si hace falta una tabla, script con el próximo número libre (sin ejecutarlo).

Primero mostrame la lista de archivos y el contrato del endpoint; después implementá.
Al final, en `backend/`, corré `uv run ruff check`, `uv run mypy`, `uv run lint-imports` y
`uv run pytest`, y pasá el checklist del agente.
