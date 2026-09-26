# Imagen del backend para Railway. Reemplazar <app> por el paquete del perfil y alinear
# PYTHON_VERSION con backend/.python-version.
ARG PYTHON_VERSION=3.13

# --- build: instala dependencias desde uv.lock en un venv ---
FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Primero solo las dependencias, para aprovechar la cache de capas.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# --- runtime: sin uv, sin herramientas de build, usuario no root ---
FROM python:${PYTHON_VERSION}-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER app
EXPOSE 8000

# Railway inyecta PORT. --proxy-headers porque el tráfico llega por el proxy de Railway.
CMD ["sh", "-c", "exec uvicorn <app>.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
