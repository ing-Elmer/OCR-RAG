---
paths:
  - "**/.env*"
  - "**/settings.py"
  - "**/main.py"
  - "**/pyproject.toml"
  - "**/Dockerfile"
  - "**/.github/workflows/*.yml"
  - "**/.gitignore"
  - "**/.claude/settings*.json"
---

# Seguridad y configuración

## Secretos
- El backend lee la configuración de variables de entorno mediante `Settings` (pydantic-settings).
  Los secretos (DSN/credenciales de PostgreSQL, signing key del JWT, passwords de sistema, API
  keys) se tipan como `SecretStr` y vienen de variables de entorno o de un gestor de secretos.
- En el repo se versiona **solo** `backend/.env.example` con los nombres de las variables y
  valores ficticios. `backend/.env` (local) **no se versiona**.
- Cada ambiente tiene secretos distintos; nunca reutilizar el mismo valor entre desarrollo y
  producción.
- La configuración base no lleva datos personales de un desarrollador (rutas locales, emails,
  perfiles de nube).
- Frontend: en `.env` solo van valores públicos (`VITE_*`). Los `.env*.local` no se versionan.
- Si se encuentra un secreto versionado: avisar al usuario sin repetirlo y proponer rotarlo.
- Claves criptográficas nunca como constantes en el código.
- Passwords con `bcrypt` (costo ≥ 12); JWT firmado con algoritmo fijo (`HS256`/`RS256`) y
  `algorithms=[...]` explícito al decodificar; refresh tokens guardados como hash y rotados en
  cada uso.

## .gitignore mínimo
`__pycache__/`, `*.py[cod]`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`,
`.coverage`, `htmlcov/`, `.env`, `.env*.local`, `node_modules/`, `dist/`, `*.log`,
`.claude/settings.local.json`, `CLAUDE.local.md`.

Si GitHub avisa de un secreto (*secret scanning* / *push protection*), no se desactiva ni se
marca como falso positivo: se avisa al usuario para rotarlo.

## CI/CD y despliegue (GitHub Actions)
- Credenciales solo como GitHub Secrets (de repositorio o, mejor, de *environment*), nunca en
  el YAML ni en el `Dockerfile`. Detalle en `ci-github.md`.
- Imagen de producción sin `--reload`, con usuario no root y dependencias instaladas desde
  `uv.lock` (`uv sync --frozen --no-dev`).
- No cambiar sitios, servicios ni destinos de deploy (los del perfil) sin confirmación.
