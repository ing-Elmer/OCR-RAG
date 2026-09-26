/**
 * Única fuente de rutas REST de la API, agrupadas por dominio.
 * Ningún service ni componente arma URLs a mano: todas salen de acá.
 */
export const endpoints = {
  health: {
    /** GET /health — anónimo. */
    check: '/health',
  },
  auth: {
    /** POST /api/auth/login — público. Devuelve el par de tokens. */
    login: '/api/auth/login',
    /** POST /api/auth/refresh — público. Rota el refresh token (el anterior queda revocado). */
    refresh: '/api/auth/refresh',
    /** POST /api/auth/logout — público. Revoca el refresh token; idempotente. */
    logout: '/api/auth/logout',
  },
  me: {
    /** GET /api/me — requiere token. */
    get: '/api/me',
  },
  documentos: {
    /** POST /api/documentos — permiso DOCUMENTOS_CARGAR. multipart/form-data (`archivo`, `idioma`). */
    crear: '/api/documentos',
    /** GET /api/documentos?limite&offset — permiso DOCUMENTOS_VER. */
    listar: '/api/documentos',
    /** GET /api/documentos/{id} — permiso DOCUMENTOS_VER. */
    obtener: (id: number): string => `/api/documentos/${id}`,
  },
  consultas: {
    /** POST /api/consultas — permiso CONSULTAS_REALIZAR. */
    crear: '/api/consultas',
  },
} as const;
