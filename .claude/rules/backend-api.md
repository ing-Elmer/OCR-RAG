---
paths:
  - "**/api/**/*.py"
  - "**/routers/**/*.py"
  - "**/main.py"
  - "**/errors.py"
  - "**/exceptions.py"
---

# Backend — routers, respuestas y errores (FastAPI)

## ApiResponse (obligatorio)
- Envelope estándar (el mismo que consume el frontend):
  `{ status: "Success" | "Created" | "Error", message, data, errors, meta }`.
- Modelo genérico `ApiResponse[T]` en `api/responses.py` con constructores
  `ApiResponse.ok(msg, data)`, `.success(msg)`, `.created(msg, data)`, `.bad_request(msg, errors)`,
  `.internal_error(msg)`.
- Todo endpoint declara `response_model=ApiResponse[<Feature>Response]` y devuelve el wrapper.
  **Nunca** devolver el DTO, un `dict` o un `JSONResponse` armado a mano.
- JSON en **camelCase**: todos los DTOs heredan de `CamelModel`
  (`alias_generator=to_camel`, `populate_by_name=True`) y se serializan por alias.
- `RequestValidationError` (body/query inválido) se traduce a **400** con el envelope y
  `errors = { campo: [mensajes] }`; nunca el 422 por defecto de FastAPI.

## Excepciones
- Las excepciones de dominio heredan de `DomainError` (en `core/exceptions.py`), que declara
  `status_code` como atributo de clase (403, 404, 409, …). Una excepción nueva **declara** su
  status; no basta con documentarlo.
- `api/errors.py` registra los exception handlers y es el único lugar que traduce excepciones:
  `RequestValidationError` y `ValidationError` de Core → 400, `DomainError` → su `status_code`,
  `UnauthorizedError` → 401, todo lo demás → 500 genérico (se loguea con `logger.exception`, el
  cliente nunca ve el detalle).
- Los routers **no** tienen `try/except` ni lanzan `HTTPException`.

## Routers
- Solo: path, dependencias, llamar al Service y envolver el resultado.
- Autenticación por defecto: cada `APIRouter` protegido declara
  `dependencies=[Depends(get_current_user)]`. Un endpoint público va en un router público y con
  un comentario que justifique por qué; ningún endpoint de alta de usuarios/credenciales puede
  ser anónimo.
- Permisos por endpoint con `Depends(require_permission("<CODIGO>"))`, no con `if` sobre el rol
  dentro de la función.
- Modelos de formulario (`UploadFile` + `Form`) en `api/forms/`, sufijo `Form`.
- Todo endpoint nuevo consumido por el frontend se agrega también en su `api/endpoints.ts`.
- Prefijo de rutas `/api/...` agrupado por dominio; `openapi_url`/`docs_url` deshabilitados en
  producción (por configuración).

## Operación
- `GET /health` anónimo (incluye `SELECT 1` contra la conexión principal).
- `CORSMiddleware` con orígenes explícitos desde `Settings`; nunca `allow_origins=["*"]` en
  producción.
- Recursos (pools de conexión, cola de tareas) se abren y cierran en el `lifespan` de la app,
  nunca al importar un módulo.
