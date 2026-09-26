---
paths:
  - "**/tests/**/*.py"
  - "**/test_*.py"
  - "**/conftest.py"
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Testing

## Backend (`backend/tests/`, pytest + pytest-asyncio + httpx)
- Un archivo de test por Service y por Validator: `tests/application/test_<feature>_service.py`.
  Nombre de cada test: `test_<metodo>_<escenario>_<resultado_esperado>`.
- Services y validators se testean instanciándolos con repositorios **fake** (clases que
  implementan el `Protocol`) o `AsyncMock`; nunca se pega a la base real ni a la nube.
- Routers: tests con `httpx.AsyncClient` + `ASGITransport` y `app.dependency_overrides` para
  reemplazar services; verifican status, envelope y permisos.
- **Obligatorio desde el día uno:** tests de autenticación (login, verificación de password,
  emisión y rotación de refresh tokens, reuso de un refresh revocado, usuario inactivo) y de
  autorización por permiso (403 sin permiso, 401 sin token).
- Tests de repositorios (opcionales) solo contra una base efímera (testcontainers), nunca
  contra una base compartida.

## Frontend (Vitest + @testing-library/react)
- Config dentro de `vite.config.ts > test`; setup en `src/test/setup.ts`.
- `renderHook` para hooks y contexts.
- **Obligatorio:** tests del interceptor de `api/api.ts` (refresh con varios 401
  concurrentes), `tokenStore` y `AuthContext`.

## Reglas
- Todo bug corregido lleva un test que lo reproduce.
- Lógica nueva en un Service, Validator o hook lleva tests en el mismo cambio.
- Nunca borrar, comentar ni saltear (`@pytest.mark.skip`, `xfail` sin motivo, `.skip`, `.only`)
  tests para que pase el build.
